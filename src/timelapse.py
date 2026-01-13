import geemap
import ee
import os

def generate_timelapse(lat, lon, start_year, end_year, place_name, output_filename, project_id=None, radius=10000, frequency='year', width=768, fps=5):
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
    roi = point.buffer(radius).bounds()

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
    vis_params = {"min": 0, "max": 0.3, "bands": ['Red', 'Green', 'Blue']}

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
        'dimensions': width,
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

    # 5. Add Text Overlay (Date)
    print("Adding date labels...")
    try:
        # Get dates from the original collection for accuracy
        dates_ms = collection.aggregate_array('system:time_start').getInfo()
        import datetime
        
        dates = []
        for ms in dates_ms:
            if ms is None: continue 
            dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
            if frequency == 'year':
                dates.append(dt.strftime('%Y'))
            elif frequency == 'quarter':
                q = (dt.month - 1) // 3 + 1
                dates.append(f"{dt.year} Q{q}")
            else: # month
                dates.append(dt.strftime('%Y-%m'))
        
        if len(dates) > 0:
             geemap.add_text_to_gif(
                 out_gif, 
                 out_gif, 
                 xy=('3%', '5%'), 
                 text_sequence=dates, 
                 font_size=30, 
                 font_color='white',
                 duration=int(1000/fps) # Duration in ms per frame
             )
        else:
            print("Warning: No dates found for text overlay.")

    except Exception as e:
        print(f"Failed to add text overlay: {e}")

    print(f"Timelapse saved to: {out_gif}")
    
    # Manually generate MP4 with quoted paths
    if os.path.exists(out_gif):
        import shutil
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
    
