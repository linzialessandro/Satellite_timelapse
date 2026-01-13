import argparse
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    parser = argparse.ArgumentParser(description="Earth-Time-Lapse: Generate satellite timelapses.")
    parser.add_argument("--place", type=str, required=True, help="Place name (e.g., 'Udine, Italy')")
    parser.add_argument("--years", type=int, default=20, help="Number of years to go back (default: 20)")
    parser.add_argument("--output", type=str, default="timelapse", help="Base name for output file (default: timelapse)")
    parser.add_argument("--project", type=str, help="Google Cloud Project ID for Earth Engine")
    parser.add_argument("--radius", type=int, default=6000, help="Radius around the location in meters (default: 6000)")
    parser.add_argument("--frequency", type=str, default="year", choices=["year", "quarter", "month"], help="Timelapse frequency (default: year)")
    parser.add_argument("--width", type=int, default=768, help="Width of the output GIF in pixels (default: 768)")
    parser.add_argument("--fps", type=int, default=10, help="Frames per second (default: 10)")
    parser.add_argument("--vertical", action="store_true", help="Generate vertical (9:16) video for mobile")
    
    args = parser.parse_args()
    
    print(f"Generating timelapse for: {args.place}")
    print(f"Duration: {args.years} years")

    # Geocoding
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="earth-time-lapse-tool")
        location = geolocator.geocode(args.place)
        
        if not location:
             print(f"Error: Could not find location '{args.place}'.")
             return
        
        lat, lon = location.latitude, location.longitude
        print(f"Found location: {location.address} ({lat}, {lon})")
        
    except ImportError:
        print("Error: 'geopy' library not found. Please pip install geopy.")
        return
    except Exception as e:
        print(f"Geocoding error: {e}")
        return

    # Time range
    import datetime
    current_year = datetime.datetime.now().year
    end_year = current_year
    start_year = current_year - args.years
    
    # Generate Timelapse
    from src.timelapse import generate_timelapse
    try:
        generate_timelapse(lat, lon, start_year, end_year, args.place, args.output, args.project, args.radius, args.frequency, args.width, args.fps, args.vertical)
    except Exception as e:
        print(f"Failed to generate timelapse: {e}")
    
if __name__ == "__main__":
    main()
