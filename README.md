# 🌍 AI Travel Planning App

> An intelligent travel planning application that generates personalized itineraries using AI agents and real-time data.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

- **AI-Powered Itinerary Generation** - Intelligent trip planning using Google Gemini AI
- **Real-Time Hotel Search** - Integration with Booking.com API for live hotel availability
- **Route Optimization** - Smart travel route planning with Google Maps integration
- **Interactive Hotel Selection** - User-friendly hotel browsing and selection interface
- **Multi-Day Planning** - Flexible itinerary creation for any trip duration
- **Geographic Clustering** - Attractions grouped by proximity for efficient travel
- **Multiple Transport Modes** - Support for walking, driving, and public transit

## 🏗️ Architecture

The application uses a multi-agent architecture with specialized AI agents:

- **Attraction Agent** - Discovers and curates local attractions
- **Booking Agent** - Handles hotel search and availability
- **Map Agent** - Optimizes routes and calculates travel times
- **Planning Graph** - Orchestrates the entire planning workflow

## 🚀 Quick Start

### Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/travel-planning-app.git
   cd travel-planning-app
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   Open http://localhost:8501 in your browser

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key"
   export BOOKING_API_KEY="your_booking_api_key"
   export DISTANCE_MATRIX_API_KEY="your_google_maps_api_key"
   export TAVILY_API_KEY="your_tavily_api_key"
   ```

3. **Run the application**
   ```bash
   streamlit run main.py
   ```

## 🔧 Configuration

### Required API Keys

| Service | Purpose | How to Obtain |
|---------|---------|---------------|
| Google Gemini | AI content generation | [Google AI Studio](https://aistudio.google.com/) |
| Booking.com API | Hotel search | [RapidAPI Booking.com](https://rapidapi.com/apidojo/api/booking/) |
| Google Maps | Distance calculations | [Google Cloud Console](https://console.cloud.google.com/) |
| Tavily | Web search (optional) | [Tavily API](https://tavily.com/) |

### Environment Variables

Create a `.env` file in the project root:

```env
# AI & Search APIs
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Maps & Location APIs
DISTANCE_MATRIX_API_KEY=your_google_maps_api_key_here

# Booking APIs
BOOKING_API_KEY=your_booking_api_key_here
BOOKING_API_HOST=booking-com.p.rapidapi.com
```

## 📖 Usage

1. **Enter Trip Details**
   - Destination city and country
   - Number of attractions desired
   - Travel focus (cultural, nature, adventure, etc.)

2. **Review Attractions**
   - Browse AI-curated list of attractions
   - View detailed descriptions and highlights

3. **Select Accommodation**
   - Browse available hotels with real-time pricing
   - Filter by preferences and budget
   - View hotel details and amenities

4. **Get Your Itinerary**
   - Receive optimized daily schedules
   - Interactive maps with routing
   - Travel time estimates between locations

## 🛠️ Development

### Project Structure

```
trip-planner/
├── backend/
│   ├── agents/           # AI agent implementations
│   │   ├── utils/        # Shared utilities
│   │   │   ├── hotel_filter.py
│   │   │   ├── json_formatter.py
│   │   │   ├── location_normalizer.py
│   │   │   ├── LocationGeocoder.py
│   │   │   ├── prompt.py
│   │   ├── attraction_agent.py
│   │   ├── booking_agent.py
│   │   ├── hotel_agent.py
│   │   ├── map_agent.py
│   │   └── prompt_agent.py
│   ├── prompts/          # AI prompt templates
│   │   ├── attraction_agent_prompt.yaml
│   │   ├── booking_agent_prompt.yaml
│   │   ├── map_agent_prompt.yaml
│   │   └── prompt_agent_prompt.yaml
│   ├── settings/
│   │   ├── config.py
│   │   └── graph.py      # Main workflow orchestration
├── frontend/
│   └── assets/           # Static assets
│   │   └── styles.css    # CSS styles
│   └── models/           # Data models
│   │   └── travel_request.py
│   └── views/            # UI components
│   │   ├── attractions.py
│   │   ├── dashboard.py
│   │   ├── export.py
│   │   ├── home.py
│   │   ├── hotels.py
│   │   ├── itinerary.py
│   │   └── utils.py
├── .dockerignore         # Docker ignore file
├── .env                  # Environment variables
├── .gitignore            # Git ignore file
├── docker-compose.yaml   # Multi-container setup
├── Dockerfile            # Container configuration
├── graph.png             # Application graph
├── LICENSE               # Project license
├── main.py               # Application entry point
├── README.md             # Project documentation
└── requirements.txt      # Python dependencies
```

### Key Components

- **Graph Architecture**: Uses LangGraph for workflow orchestration
- **Agent Pattern**: Specialized AI agents for different planning tasks
- **State Management**: Persistent state across planning stages
- **Error Handling**: Robust error recovery and fallback mechanisms

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Check code quality
flake8 backend/ frontend/
black backend/ frontend/
```

## 🐳 Docker Support

### Production Deployment

```bash
# Build and run in production mode
docker-compose -f docker-compose.prod.yml up -d
```

### Development with Hot Reload

```bash
# Run with volume mounting for development
docker-compose up
```

### Health Checks

The application includes built-in health checks accessible at:
- http://localhost:8501/_stcore/health

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code style
- Add tests for new features
- Update documentation for API changes
- Use conventional commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/travel-planning-app/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/travel-planning-app/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/travel-planning-app/wiki)

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing web framework
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Google Gemini](https://ai.google.dev/) for AI capabilities
- [Booking.com](https://booking.com) for hotel data

## 🔮 Roadmap

- [ ] Multi-language support
- [ ] Flight booking integration
- [ ] Mobile responsive design
- [ ] Offline map support
- [ ] User accounts and saved trips
- [ ] Social sharing features
- [ ] Weather integration
- [ ] Budget tracking

---

**Made with ❤️ by [Your Name](https://github.com/yourusername)**

*Happy travels! 🎒✈️*
