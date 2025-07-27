# AFRT - Antisemitic Hate Speech Detection on Reddit

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AFRT is a comprehensive pipeline for detecting and analyzing antisemitic hate speech on Reddit. The system combines multi-threaded data collection, toxicity scoring via Google's Perspective API, and advanced antisemitism detection using Google's Gemini LLM.

## 🎯 Overview

The AFRT pipeline consists of five main stages:

1. **Data Gathering** - Multi-threaded collection of Reddit posts and comments from specified subreddits
2. **Data Processing** - Conversion and composition of conversation threads for analysis
3. **Perspective API Assessment** - Toxicity scoring using Google's Perspective API
4. **Conversation Sorting** - Ranking conversations by maximum toxicity scores
5. **Gemini LLM Assessment** - Advanced antisemitism detection using Gemini 2.5 Flash

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Reddit API credentials
- Google Perspective API key
- Google Gemini API key
- Google Sheets API credentials

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd AFRT
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:

   ```env
   # Reddit API
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USERNAME=your_reddit_username

   # Google APIs
   PERSPECTIVE_API_KEY=your_perspective_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Configure Google Sheets API**

   - Download `client_secrets.json` from Google Cloud Console
   - Place it in the project root directory

5. **Verify required files**
   Ensure these files exist:
   - `targeting.json` - Configuration file
   - `llm/prompts/detection_prompt.md` - Gemini detection prompt
   - `data/schemas/geminis_llm_schema.json` - Gemini output schema

### Running the Pipeline

**Complete pipeline:**

```bash
python main.py
```

**Specific stages:**

```bash
# Data gathering only
python main.py --stages gather

# Data processing and conversation composition
python main.py --stages process

# Perspective API assessment
python main.py --stages perspective

# Sort conversations by score
python main.py --stages sort

# Gemini LLM assessment
python main.py --stages gemini
```

**Custom parameters:**

```bash
# Custom number of posts per subreddit
python main.py --num-posts 100

# Custom batch size for API processing
python main.py --batch-size 25

# Filter by specific toxicity attributes
python main.py --required-attributes toxicity,severe_toxicity,identity_attack
```

## 📁 Project Structure

```
AFRT/
├── main.py                          # Main pipeline orchestrator
├── multi_threaded_gather.py         # Stage 1: Data gathering
├── data_processing.py               # Stage 2: Data processing
├── perspective_assessment.py        # Stage 3: Perspective API assessment
├── gemini_assessment.py             # Stage 5: Gemini LLM assessment
├── reddit_api.py                    # Reddit API utilities
├── utils.py                         # Utility functions
├── targeting.json                   # Configuration file
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (create this)
├── client_secrets.json              # Google Sheets API credentials
├── data/
│   ├── schemas/                     # JSON schemas
│   ├── subreddits/                  # Collected data by subreddit
│   ├── posts.csv                    # Processed posts data
│   ├── comments.csv                 # Processed comments data
│   ├── conversations.csv            # Composed conversation threads
│   ├── perspectives.csv             # Perspective API results
│   └── conversations_sorted_by_score.csv  # Ranked conversations
├── llm/
│   ├── prompts/
│   │   └── detection_prompt.md      # Gemini detection prompt
│   ├── logs/                        # Error logs
│   ├── perspective_api.py           # Perspective API client
│   ├── gemini_api.py                # Gemini API client
│   ├── perspective_logger.py        # Perspective error logging
│   └── gemini_logger.py             # Gemini error logging
└── submodules/
    └── google_api/                  # Google Sheets API utilities
```

## 🔧 Configuration

### Targeting Configuration (`targeting.json`)

The targeting configuration defines:

- **Subreddits**: List of subreddits to monitor
- **Search Terms**: Antisemitic and neutral search terms for data collection
- **Perspective API Attributes**: Toxicity attributes to analyze
- **Google Sheets Configuration**: Spreadsheet and sheet IDs

### Environment Variables

Required environment variables:

- `REDDIT_CLIENT_ID` - Reddit API client ID
- `REDDIT_CLIENT_SECRET` - Reddit API client secret
- `REDDIT_USERNAME` - Reddit username
- `PERSPECTIVE_API_KEY` - Google Perspective API key
- `GEMINI_API_KEY` - Google Gemini API key

## 📊 Output Files

### CSV Files

- `data/posts.csv` - Reddit posts data
- `data/comments.csv` - Reddit comments data
- `data/conversations.csv` - Composed conversation threads
- `data/perspectives.csv` - Perspective API toxicity scores
- `data/conversations_sorted_by_score.csv` - Ranked conversations

### Google Sheets

The system automatically creates and populates Google Sheets with:

- Posts data
- Comments data
- Perspective API assessments
- Gemini LLM assessments

### Log Files

- `llm/logs/perspective_errors_*.log` - Perspective API errors
- `llm/logs/gemini_errors_*.log` - Gemini API errors

## 🔍 Pipeline Stages

### Stage 1: Data Gathering

- Multi-threaded collection from Reddit subreddits
- Uses targeted search terms for comprehensive coverage
- Applies rate limiting to respect API limits
- Saves data to Google Sheets and local JSON files

### Stage 2: Data Processing

- Converts Google Sheets data to CSV format
- Composes full conversation threads from posts and comments
- Builds hierarchical comment trees with proper indentation
- Handles missing data and edge cases

### Stage 3: Perspective API Assessment

- Scores conversations for toxicity using Google's Perspective API
- Analyzes multiple attributes: TOXICITY, SEVERE_TOXICITY, IDENTITY_ATTACK, etc.
- Handles rate limiting and error recovery
- Logs errors for debugging

### Stage 4: Conversation Sorting

- Sorts conversations by maximum toxicity scores
- Optionally filters by specific toxicity attributes
- Prioritizes high-risk content for further analysis

### Stage 5: Gemini LLM Assessment

- Advanced antisemitism detection using Gemini 2.5 Flash
- Uses sophisticated prompt engineering for comprehensive detection
- Identifies explicit and implicit antisemitic content
- Provides detailed reasoning and confidence levels

## 🛠️ API Integration

### Reddit API

- PRAW-based Reddit client
- Functions for fetching posts, comments, and user data
- Search functionality with filtering options
- Rate limiting and error handling

### Google Perspective API

- Toxicity attribute analysis
- Response cleaning and formatting
- Schema generation
- Comprehensive error handling

### Google Gemini API

- Gemini 2.5 Flash client
- Structured output generation
- System instruction support
- Token management

## 🔒 Security and Privacy

- Environment variable-based configuration
- No hardcoded credentials
- Secure credential storage
- Local data storage with proper permissions
- No sensitive data in logs

## 📈 Performance Considerations

### Rate Limiting

- Reddit API: 0.6s between requests
- Perspective API: 1.1s between requests
- Gemini API: 1.1s between requests

### Batch Processing

- Configurable batch sizes for API calls
- Memory-efficient processing of large datasets
- Progress tracking for long-running operations

### Multi-threading

- Parallel subreddit processing in data gathering
- Thread-safe logging and error handling
- Configurable thread counts

## 🐛 Troubleshooting

### Common Issues

1. **Missing Environment Variables**

   - Check `.env` file exists and contains all required variables
   - Verify API keys are valid and have proper permissions

2. **Google Sheets API Errors**

   - Ensure `client_secrets.json` is properly configured
   - Check Google Sheets API is enabled in Google Cloud Console

3. **Rate Limiting Issues**

   - Increase delays between API requests
   - Reduce batch sizes for processing
   - Check API quotas and limits

4. **Memory Issues**
   - Reduce batch sizes
   - Process data in smaller chunks
   - Monitor system resources

### Debug Mode

Enable detailed logging by modifying log levels in the logger setup functions.

## 📚 Documentation

For detailed documentation, see:

- [Pipeline Documentation](PIPELINE_DOCUMENTATION.md) - Comprehensive guide to the pipeline
- [API Documentation](reddit_api.py) - Reddit API utilities
- [Configuration Guide](targeting.json) - Configuration options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is designed for research and educational purposes in hate speech detection and analysis.

## 🆘 Support

For issues and questions:

1. Check the error logs in `llm/logs/`
2. Verify all required files and environment variables
3. Review the configuration in `targeting.json`
4. Test individual stages with smaller datasets

## 🔮 Future Enhancements

- Real-time monitoring capabilities
- Advanced filtering and search options
- Machine learning model integration
- Web-based dashboard
- Automated alerting system
- Cloud deployment options
- Database integration
- Distributed processing

---

**Note**: This project is designed for research and educational purposes in hate speech detection and analysis. Please ensure compliance with all applicable laws and platform terms of service when using this tool.
