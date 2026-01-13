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

    # 1. Get Harmonized Landsat Time Series (Composites)
    # geemap.landsat_timeseries returns a collection with renamed bands ['Red', 'Green', 'Blue', ...]
    collection = geemap.landsat_timeseries(
        roi=roi,
        start_year=start_year,
        end_year=end_year,
        start_date='01-01',
        end_date='12-31',
        frequency=frequency
    ).select(['Red', 'Green', 'Blue']).map(lambda img: img.toFloat())

    # 2. Apply Temporal Smoothing (Moving Median)
    # Define window size (radius) based on frequency
    # We want a window of approx +/- 1 step.
    if frequency == 'year':
        window_size = 1
        unit = 'year'
    elif frequency == 'quarter':
        window_size = 1 
        unit = 'year' # Quarters are hard, treat as +/- 0.25 year (approx 3 months) or just use months 
        # Actually 'advance' doesn't support quarter. Let's use months.
        window_size = 4 # 1 quarter = 3 months. Radius 4 months covers neighbors.
        unit = 'month'
    elif frequency == 'month':
        window_size = 2 # Radius 2 months (approx 5 month window total)
        unit = 'month'
    else:
         window_size = 1
         unit = 'year'

    print(f"Applying temporal smoothing (Moving Median) with radius {window_size} {unit}(s)...")

    def smooth_func(image):
        d = ee.Date(image.get('system:time_start'))
        # Create a window: [d - window, d + window]
        # Advance arguments: delta, unit
        start_win = d.advance(-window_size, unit)
        end_win = d.advance(window_size, unit) 
        
        # Filter the original collection
        subset = collection.filterDate(start_win, end_win)
        
        # Reduce to Median
        composite = subset.median()
        
        # Restore time property for sorting
        return composite.set('system:time_start', image.get('system:time_start'))

    smoothed_collection = collection.map(smooth_func)

    # 3. Visualization configuration
    # Landsat surface reflectance: 0 to 0.3 typically for RGB
    vis_params = {"min": 0, "max": 0.3, "bands": ['Red', 'Green', 'Blue']}

    # 4. Export Video
    # Construct filename if using default
    clean_place = place_name.split(',')[0].strip().replace(' ', '_')
    if output_filename == "timelapse":
        output_filename = f"timelapse_{clean_place}"
    
    if not output_filename.endswith('.gif'):
        out_gif = output_filename + ".gif"
        out_mp4 = output_filename + ".mp4"
    else:
        out_gif = output_filename
        out_mp4 = output_filename.replace('.gif', '.mp4')
        
    print(f"Downloading timelapse video to {out_gif}...")
    
    # We visualize the collection first to bake in the styles
    # visualize() returns 3 bands (vis-red, vis-green, vis-blue) byte values
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
        # Get dates from the smoothed collection. 
        # Note: system:date was set in smooth_func but might be a tuple. 
        # We need a string list.
        # Let's get the 'system:time_start' and format it.
        dates_ms = smoothed_collection.aggregate_array('system:time_start').getInfo()
        import datetime
        
        dates = []
        for ms in dates_ms:
            # Convert millisecond timestamp to date string
            dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
            if frequency == 'year':
                dates.append(dt.strftime('%Y'))
            elif frequency == 'quarter':
                # Custom format YYYY Qx
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
    
