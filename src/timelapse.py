import geemap
import ee
import os
import shutil
from PIL import Image, ImageDraw, ImageFont

def generate_timelapse(lat, lon, start_year, end_year, place_name, output_filename, project_id=None, radius=10000, frequency='year', width=768, fps=10, vertical=False):
    """
    Generates a satellite timelapse for the given coordinates and time range.
    Applies temporal smoothing to reduce flickering.
    """
    try:
        # Initialize Earth Engine
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
        print("Earth Engine initialized successfully.")
    except Exception as e:
        if "no project found" in str(e).lower():
             print("\nError: Earth Engine project not found.")
             print("Please specify a project ID using '--project <YOUR_PROJECT_ID>'")
             print("OR set a default project by running: earthengine set_project <YOUR_PROJECT_ID>\n")
        else:
             print(f"Earth Engine initialization failed: {e}")
             print("Please ensure you are authenticated by running 'earthengine authenticate'.")
        raise e

    # Define the Region of Interest (ROI)
    point = ee.Geometry.Point([lon, lat])
    
    video_dims = width
    if vertical:
        print("Configuring for Vertical Video (9:16)...")
        # Vertical ratio 9:16 - Adjust width/height to match coverage
        height_radius = radius * (16/9)
        
        # Calculate bounds for vertical ROI
        try:
            poly_w = point.buffer(radius).bounds().getInfo()['coordinates'][0]
            poly_h = point.buffer(height_radius).bounds().getInfo()['coordinates'][0]
            
            lons = [p[0] for p in poly_w]
            lats = [p[1] for p in poly_h]
            
            roi = ee.Geometry.Rectangle([min(lons), min(lats), max(lons), max(lats)])
            video_dims = [720, 1280] # 720p Vertical (Safe for EE limits)
        except Exception as e:
            print(f"Error calculating vertical ROI: {e}. Falling back to standard.")
            roi = point.buffer(radius).bounds()
            video_dims = [width, int(width * 16/9)]
            
    else:
        roi = point.buffer(radius).bounds()
        video_dims = width

    print(f"Generating timelapse for {place_name} ({lat}, {lon}) from {start_year} to {end_year}...")
    print(f"Settings: Frequency={frequency}, Radius={radius}m, Width={width}px, FPS={fps}")

    # 1. Get Harmonized Landsat Time Series
    collection = geemap.landsat_timeseries(
        roi=roi,
        start_year=start_year,
        end_year=end_year,
        start_date='01-01',
        end_date='12-31',
        frequency=frequency
    ).select(['Red', 'Green', 'Blue']).map(lambda img: img.toFloat())

    # 2. Apply Temporal Smoothing (Moving Median)
    if frequency == 'year':
        window_size, unit = 1, 'year'
    elif frequency == 'quarter':
        window_size, unit = 4, 'month' # Approx 1 quarter
    elif frequency == 'month':
        window_size, unit = 2, 'month'
    else:
         window_size, unit = 1, 'year'

    print(f"Applying temporal smoothing (Moving Median) with radius {window_size} {unit}(s)...")

    def smooth_func(image):
        d = ee.Date(image.get('system:time_start'))
        start_win = d.advance(-window_size, unit)
        end_win = d.advance(window_size, unit) 
        
        subset = collection.filterDate(start_win, end_win)
        return subset.median().set('system:time_start', image.get('system:time_start'))

    smoothed_collection = collection.map(smooth_func)

    # 3. Visualization configuration
    # Natural color with standard deviation stretch (approx sigma=2)
    vis_params = {"min": 0.0, "max": 0.25, "bands": ['Red', 'Green', 'Blue'], "gamma": 1.2}

    # 4. Export Video
    clean_place = place_name.split(',')[0].strip().replace(' ', '_')
    if output_filename == "timelapse":
        output_filename = f"timelapse_{clean_place}"
    
    if not output_filename.endswith('.gif'):
        out_gif, out_mp4 = output_filename + ".gif", output_filename + ".mp4"
    else:
        out_gif, out_mp4 = output_filename, output_filename.replace('.gif', '.mp4')
        
    print(f"Downloading timelapse video to {out_gif}...")
    
    rgb_collection = smoothed_collection.map(lambda img: img.visualize(**vis_params))

    video_args = {
        'dimensions': video_dims,
        'region': roi,
        'framesPerSecond': fps,
        'crs': 'EPSG:3857',
        'min': 0,
        'max': 255,
    }

    geemap.download_ee_video(
        rgb_collection,
        video_args,
        out_gif
    )

    # 5. Add Text Overlay (Date & Location)
    print("Adding aesthetic text overlays...")
    try:
        # Get dates
        dates_ms = collection.aggregate_array('system:time_start').getInfo()
        import datetime
        
        dates = []
        for ms in dates_ms:
            if ms is None: 
                dates.append("")
                continue
            dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
            if frequency == 'year':
                dates.append(dt.strftime('%Y'))
            elif frequency == 'quarter':
                q = (dt.month - 1) // 3 + 1
                dates.append(f"{dt.year} Q{q}")
            else: 
                dates.append(dt.strftime('%Y-%m'))

        if len(dates) > 0 and os.path.exists(out_gif):
            # Process GIF frames with PIL
            with Image.open(out_gif) as im:
                frames = []
                # Loop over frames
                for i in range(im.n_frames):
                    im.seek(i)
                    frame = im.convert("RGBA")
                    
                    # Prepare drawing
                    draw = ImageDraw.Draw(frame)
                    w, h = frame.size
                    
                    # Fonts
                    try:
                        font_size_year = int(h * 0.05)
                        font_size_loc = int(h * 0.03)
                        
                        # Try loading system fonts
                        font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                        if not os.path.exists(font_path):
                             font_path = "/System/Library/Fonts/Helvetica.ttc"
                        
                        if os.path.exists(font_path):
                            font_year = ImageFont.truetype(font_path, font_size_year)
                            font_loc = ImageFont.truetype(font_path, font_size_loc)
                        else:
                            font_year = ImageFont.load_default()
                            font_loc = ImageFont.load_default()
                    except:
                        font_year = ImageFont.load_default()
                        font_loc = ImageFont.load_default()

                    # Text Content
                    text_year = dates[i] if i < len(dates) else ""
                    text_loc = place_name
                    
                    # padding
                    pad = 20
                    
                    # 1. Year (Top-Right)
                    if text_year:
                        bbox = draw.textbbox((0, 0), text_year, font=font_year)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        
                        x_year = w - text_w - pad
                        y_year = pad
                        
                        # Background (Semi-transparent black)
                        overlay = Image.new('RGBA', frame.size, (0,0,0,0))
                        d_over = ImageDraw.Draw(overlay)
                        d_over.rectangle([x_year - 10, y_year - 5, x_year + text_w + 10, y_year + text_h + 5], fill=(0, 0, 0, 100))
                        frame = Image.alpha_composite(frame, overlay)
                        draw = ImageDraw.Draw(frame) # re-init draw on new frame
                        
                        # Draw Text
                        draw.text((x_year, y_year), text_year, font=font_year, fill="white")

                    # 2. Location (Bottom-Left)
                    if text_loc:
                        bbox = draw.textbbox((0, 0), text_loc, font=font_loc)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        
                        x_loc = pad
                        y_loc = h - text_h - pad - 10 # extra bottom margin
                        
                        # Background
                        overlay = Image.new('RGBA', frame.size, (0,0,0,0))
                        d_over = ImageDraw.Draw(overlay)
                        d_over.rectangle([x_loc - 10, y_loc - 5, x_loc + text_w + 10, y_loc + text_h + 5], fill=(0, 0, 0, 100))
                        frame = Image.alpha_composite(frame, overlay)
                        draw = ImageDraw.Draw(frame)
                        
                        draw.text((x_loc, y_loc), text_loc, font=font_loc, fill="white")
                    
                    frames.append(frame)

                # Save new GIF
                frames[0].save(
                    out_gif,
                    save_all=True,
                    append_images=frames[1:],
                    duration=im.info.get('duration', 100),
                    loop=0
                )

        else:
            print("Warning: No dates found or output file missing.")

    except Exception as e:
        print(f"Failed to add text overlay: {e}")

    print(f"Timelapse saved to: {out_gif}")
    
    # Generate MP4
    if os.path.exists(out_gif):
        if shutil.which("ffmpeg"):
            print("Generating MP4...")
            cmd = f'ffmpeg -y -i "{out_gif}" -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" "{out_mp4}"'
            result = os.system(cmd)
            if result == 0:
                print(f"MP4 saved to: {out_mp4}")
            else:
                 print("Failed to generate MP4 (ffmpeg error).")
        else:
            print("ffmpeg not found, skipping MP4 generation.")

    return out_gif
    
