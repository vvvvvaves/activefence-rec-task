# AFRT - Antisemitic Hate Speech Detection Pipeline

## Overview

AFRT (Antisemitic Hate Speech Detection on Reddit) is a comprehensive pipeline designed to detect and analyze antisemitic hate speech on Reddit. The system uses a multi-stage approach combining Reddit data collection, toxicity scoring via Google's Perspective API, and advanced antisemitism detection using Google's Gemini LLM.

## System Architecture

The pipeline consists of five main stages:

1. **Data Gathering** - Multi-threaded collection of Reddit posts and comments
2. **Data Processing** - Conversion and composition of conversation threads
3. **Perspective API Assessment** - Toxicity scoring using Google's Perspective API
4. **Conversation Sorting** - Ranking conversations by maximum toxicity scores
5. **Gemini LLM Assessment** - Advanced antisemitism detection using Gemini 2.5 Flash

## Pipeline Stages

### Stage 1: Data Gathering (`multi_threaded_gather.py`)

**Purpose**: Collect Reddit posts and comments from specified subreddits using targeted search terms.

**Input**:

- Configuration from `targeting.json` (subreddits, search terms)
- Reddit API credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME)

**Process**:

- Creates multiple threads (one per subreddit)
- Each thread searches for posts using antisemitic and neutral search terms
- Collects posts and their associated comments
- Applies rate limiting (0.6s between Reddit requests, 1s between Perspective requests)
- Saves data to Google Sheets and local JSON files

**Output**:

- Google Sheets populated with posts and comments
- Local JSON files in `data/subreddits/{subreddit}/posts/` and `data/subreddits/{subreddit}/comments/`

**Key Features**:

- Multi-threaded processing for efficiency
- Rate limiting to respect API limits
- Progress bars for monitoring
- Error handling and logging
- Automatic Google Sheets integration

### Stage 2: Data Processing (`data_processing.py`)

**Purpose**: Convert gathered data into structured conversation threads for analysis.

**Input**:

- Google Sheets with posts and comments data
- Or existing CSV files if available

**Process**:

- Converts Google Sheets data to CSV format
- Composes full conversation threads from posts and comments
- Builds hierarchical comment trees with proper indentation
- Handles missing data and edge cases

**Output**:

- `data/posts.csv` - Structured post data
- `data/comments.csv` - Structured comment data
- `data/conversations.csv` - Full conversation threads

**Key Functions**:

- `compose_conversations()` - Creates conversation trees
- `to_csv()` - Converts Google Sheets to CSV
- `sort_conversations_by_score()` - Sorts by toxicity scores

### Stage 3: Perspective API Assessment (`perspective_assessment.py`)

**Purpose**: Score conversations for toxicity using Google's Perspective API.

**Input**:

- `data/conversations.csv` with full conversation threads

**Process**:

- Processes conversations in batches (default: 50)
- Sends text to Perspective API for toxicity analysis
- Analyzes multiple attributes: TOXICITY, SEVERE_TOXICITY, IDENTITY_ATTACK, INSULT, PROFANITY, THREAT, ATTACK_ON_AUTHOR, ATTACK_ON_COMMENTER, INFLAMMATORY
- Handles rate limiting and error recovery
- Logs errors for debugging

**Output**:

- Google Sheets populated with Perspective API scores
- `data/perspectives.csv` - Toxicity assessments
- Error logs in `llm/logs/perspective_errors_*.log`

**Key Features**:

- Batch processing for efficiency
- Rate limiting (1.1s between requests)
- Comprehensive error handling
- Detailed logging of failures
- Automatic retry on rate limit errors

### Stage 4: Conversation Sorting (`data_processing.py`)

**Purpose**: Sort conversations by their maximum toxicity scores to prioritize high-risk content.

**Input**:

- `data/conversations.csv` - Conversation threads
- `data/perspectives.csv` - Perspective API scores

**Process**:

- Merges conversation data with toxicity scores
- Identifies maximum score and corresponding attribute for each conversation
- Sorts conversations by maximum score (descending)
- Optionally filters by specific toxicity attributes

**Output**:

- `data/conversations_sorted_by_score.csv` - Ranked conversations

**Key Features**:

- Flexible attribute filtering
- Score range reporting
- Maintains conversation context
- Handles missing data gracefully

### Stage 5: Gemini LLM Assessment (`gemini_assessment.py`)

**Purpose**: Perform advanced antisemitism detection using Google's Gemini 2.5 Flash LLM.

**Input**:

- `data/conversations_sorted_by_score.csv` (preferred) or `data/conversations.csv`

**Process**:

- Loads detection prompt from `llm/prompts/detection_prompt.md`
- Uses structured output schema from `data/schemas/geminis_llm_schema.json`
- Processes conversations in batches
- Analyzes each conversation for antisemitic content
- Provides detailed reasoning and confidence levels

**Output**:

- Google Sheets populated with Gemini assessments
- Structured antisemitism detection results
- Error logs in `llm/logs/gemini_errors_*.log`

**Key Features**:

- Advanced prompt engineering for antisemitism detection
- Structured JSON output
- Comprehensive error handling
- Token usage tracking
- Rate limiting and retry logic

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username

# Google APIs
PERSPECTIVE_API_KEY=your_perspective_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Targeting Configuration (`targeting.json`)

The targeting configuration defines:

- **Subreddits**: List of subreddits to monitor
- **Search Terms**: Antisemitic and neutral search terms for data collection
- **Perspective API Attributes**: Toxicity attributes to analyze
- **Google Sheets Configuration**: Spreadsheet and sheet IDs

### Required Files

- `client_secrets.json` - Google Sheets API credentials
- `llm/prompts/detection_prompt.md` - Gemini detection prompt
- `data/schemas/geminis_llm_schema.json` - Gemini output schema

## Usage

### Running the Complete Pipeline

```bash
python main.py
```

### Running Specific Stages

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

# Multiple stages
python main.py --stages gather,process,perspective
```

### Custom Parameters

```bash
# Custom number of posts per subreddit
python main.py --num-posts 100

# Custom batch size for API processing
python main.py --batch-size 25

# Custom context size limit
python main.py --context-size 15000

# Filter by specific toxicity attributes
python main.py --required-attributes toxicity,severe_toxicity,identity_attack
```

## Output Files

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

## Key Components

### API Modules

#### Reddit API (`reddit_api.py`)

- PRAW-based Reddit client
- Functions for fetching posts, comments, and user data
- Search functionality with filtering options
- Rate limiting and error handling

#### Perspective API (`llm/perspective_api.py`)

- Google Perspective API client
- Toxicity attribute analysis
- Response cleaning and formatting
- Schema generation

#### Gemini API (`llm/gemini_api.py`)

- Google Gemini 2.5 Flash client
- Structured output generation
- System instruction support
- Token management

### Data Processing (`data_processing.py`)

- Conversation composition from posts and comments
- CSV conversion utilities
- Score-based sorting and filtering
- Data validation and cleaning

### Utilities (`utils.py`)

- Google Sheets API integration
- Data conversion utilities
- Configuration management
- File handling functions

## Error Handling

The system includes comprehensive error handling:

### API Rate Limiting

- Automatic retry on rate limit errors
- Configurable delays between requests
- Progress tracking and recovery

### Data Validation

- Input validation for all stages
- Graceful handling of missing data
- File existence checks

### Logging

- Structured error logging with timestamps
- Detailed error context (post ID, text length, etc.)
- Separate log files for different components

## Performance Considerations

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

## Security and Privacy

### API Key Management

- Environment variable-based configuration
- No hardcoded credentials
- Secure credential storage

### Data Handling

- Local data storage with proper permissions
- Google Sheets integration with service accounts
- No sensitive data in logs

## Monitoring and Debugging

### Progress Tracking

- Real-time progress bars for all stages
- Detailed timing information
- Success/failure reporting

### Error Analysis

- Comprehensive error logging
- Contextual error information
- Recovery suggestions

### Data Quality

- Input validation at each stage
- Data completeness checks
- Output verification

## Future Enhancements

### Potential Improvements

- Real-time monitoring capabilities
- Advanced filtering and search options
- Machine learning model integration
- Web-based dashboard
- Automated alerting system

### Scalability

- Cloud deployment options
- Database integration
- Distributed processing
- API optimization

## Troubleshooting

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

## Support

For issues and questions:

1. Check the error logs in `llm/logs/`
2. Verify all required files and environment variables
3. Review the configuration in `targeting.json`
4. Test individual stages with smaller datasets

## License

This project is designed for research and educational purposes in hate speech detection and analysis.
