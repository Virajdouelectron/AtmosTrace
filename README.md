# AtmosTrace 🌍

A real-time meteor tracking visualization platform that displays meteor entries and impact zones on an interactive 3D Earth.

## Features

- Real-time meteor data from NASA's CNEOS Fireball API
- Interactive 3D globe visualization using Globe.gl
- Animated meteor entry arcs
- Color-coded impact points based on magnitude
- Responsive design for mobile and desktop
- Auto-updating data every 60 seconds

## Tech Stack

- Frontend: HTML, Tailwind CSS, JavaScript
- Backend: Python (Flask)
- Visualization: Globe.gl
- Data Source: NASA CNEOS Fireball API

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Virajdouelectron/AtmosTrace.git
cd AtmosTrace
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://localhost:8080
```

## API Endpoints

- `GET /`: Main application page
- `GET /api/meteors`: Returns latest meteor data

## Environment Variables

- `FLASK_ENV`: Set to 'development' for debug mode
- `NASA_API_URL`: NASA CNEOS Fireball API endpoint
- `PORT`: Server port (default: 8080)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NASA CNEOS for providing the meteor data
- Globe.gl for the 3D visualization library
- Flask for the web framework 