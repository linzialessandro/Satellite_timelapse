# Earth-Time-Lapse 🌍⏳

**Earth-Time-Lapse** is a powerful Python CLI tool that generates stunning satellite timelapse videos of any location on Earth using **Google Earth Engine (GEE)** and **Landsat** imagery.

Watch urban expansion, deforestation, glacia retreat, or seasonal changes over the last 40 years. The tool automatically handles cloud masking, temporal smoothing, and video generation.

## Features ✨

*   **Any Location**: Generate timelapses for any place name (e.g., "Tokyo", "Grand Canyon") or coordinates.
*   **Flexible Frequencies**: Choose between **Yearly**, **Quarterly**, or **Monthly** timelapses.
*   **Temporal Smoothing**: Advanced **Moving Median** filter to reduce cloud flickering and create smooth transitions.
*   **Date Overlays**: Automatically adds date labels (Year, Quarter, or Month) to the video.
*   **Dual Output**: Generates both high-quality **GIF** and **MP4** formats.
*   **Customizable**: Control the speed (FPS), zoom (radius), and resolution (width).
*   **Automatic Zoom**: Focuses on your target with adjustable radius.

## Prerequisites 🛠️

1.  **Python 3.8+**
2.  **Google Earth Engine Account**: [Sign up here](https://earthengine.google.com/signup/)
3.  **Google Cloud Project**: Required for authentication (free for non-commercial use).
4.  **FFmpeg**: Required for MP4 generation.
    *   **Mac**: `brew install ffmpeg`
    *   **Windows/Linux**: Install via your package manager or download from [ffmpeg.org](https://ffmpeg.org/).

### Setting up a Free Educational Project

1.  Go to [Earth Engine Signup](https://earthengine.google.com/signup/).
2.  Select **"Noncommercial"** or **"Unpaid usage"** (e.g., for Academia & Research).
3.  Select **"Create a new Google Cloud Project"** during the sign-up flow.
4.  Name your project (e.g., `ee-timelapse-user`) and note the **Project ID** (e.g., `ee-timelapse-user`).
5.  Complete the signup. This project ID will be used in the `earthengine authenticate` step.

## Installation 📦

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/earth-time-lapse.git
    cd earth-time-lapse
    ```

2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Authenticate with Earth Engine:
    ```bash
    earthengine authenticate
    ```
    Follow the browser instructions.

5.  Set your default project (Important!):
    ```bash
    earthengine set_project <YOUR_PROJECT_ID>
    ```

## Usage 🚀

Run the tool from the command line using `main.py`.

### Basic Example (Yearly)
Generate a 20-year timelapse of Udine, Italy:
```bash
python main.py --place "Udine, Italy" --years 20
```

### Detailed Quarterly Timelapse
Generate a smoother, quarterly timelapse over 10 years, playing at 8 FPS:
```bash
python main.py --place "Szczecin, Poland" --years 10 --frequency quarter --fps 8
```

### Monthly Timelapse (Slow & Detailed)
For a very detailed monthly view (requires smaller width to avoid size limits):
```bash
python main.py --place "Dubai" --years 5 --frequency month --width 400
```

### Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--place` | Location name (e.g., "New York", "Paris") | **Required** |
| `--years` | Number of years to go back from today | `20` |
| `--frequency` | Temporal step: `year`, `quarter`, or `month` | `year` |
| `--width` | Output GIF width in pixels. Reduce for monthly/long queries. | `768` |
| `--radius` | Radius around the location in meters. Smaller = closer zoom. | `10000` (10km) |
| `--fps` | Frames per second (playback speed). | `5` |
| `--output` | Base name for the output file. | `timelapse_<City>` |
| `--project` | Google Cloud Project ID (if not set globally). | None |

## Troubleshooting ❓

*   **Earth Engine Initialization Error**: Ensure you ran `earthengine authenticate` and `earthengine set_project`.
*   **Command not found: earthengine**: Activate your venv: `source venv/bin/activate`.
*   **Request payload size exceeded**: If using `month` frequency or long durations, reduce the `--width` (e.g., to 500 or 400).
*   **ffmpeg not found**: Install FFmpeg to enable MP4 generation. The tool will still generate a GIF.
*   **Black images**: Ensure using recent years. Landsat 7/8/9 coverage varies globally.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author ✍️

Built with ❤️ by Alessandro.
