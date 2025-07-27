# Anti-Semitism Detection Pipeline - Technical Specification

## 1. Deliverables Summary

### 1.1 Data Deliverables

**Raw Data Collection**:

- **60 Reddit Posts**: Complete collection of Reddit posts from targeted subreddits with full metadata including post ID, title, content, author, subreddit, and timestamp
- **5,500+ Comments**: Comprehensive collection of comments associated with the collected posts, including comment ID, content, author, parent relationships, and posting timestamps
- **JSON Data Files**: Raw data stored in structured JSON format organized by subreddit in `data/subreddits/{subreddit}/posts/` and `data/subreddits/{subreddit}/comments/` directories

**Processed Data Structures**:

- **Flattened Conversation Trees**: Complete conversations composed from posts and comments, formatted as single string variables with hierarchical indentation suitable for direct LLM processing. Each conversation maintains full context while being optimized for AI analysis
- **CSV Data Files**: Structured data in CSV format including `posts.csv`, `comments.csv`, `conversations.csv`, and `conversations_sorted_by_score.csv` for analysis and integration

**Toxicity Assessment Results**:

- **Perspective API Scores**: Complete toxicity scoring for all collected content with detailed attribute breakdowns including:
  - `TOXICITY`: General toxicity levels (0.0-1.0 scale)
  - `SEVERE_TOXICITY`: High-severity toxic content identification
  - `IDENTITY_ATTACK`: Attacks targeting identity groups
  - `INFLAMMATORY`: Content designed to provoke reactions
  - `THREAT`: Threatening language detection
  - `ATTACK_ON_AUTHOR`: Direct attacks on post authors
  - `ATTACK_ON_COMMENTER`: Attacks targeting commenters
  - Additional perspective attributes for comprehensive toxicity assessment

**Anti-Semitism Detection Results**:

- **Gemini LLM Assessments**: Detailed anti-Semitism detection results including:
  - Binary classification (antisemitic/not antisemitic) for each piece of content
  - Confidence scores (0.0-1.0 scale) for each assessment
  - Detailed reasoning explaining why content was classified as antisemitic or not
  - Severity levels for detected antisemitic content
  - Post ID, comment ID, and user ID associations
  - Subreddit context for each detection

**Adaptive Learning Data**:

- **Prompt Improvement Suggestions**: AI-generated recommendations for enhancing detection prompts based on encountered content patterns
- **Detection Pattern Analysis**: Insights into emerging antisemitic language trends and communication patterns

### 1.2 Technical Deliverables

**Complete Pipeline Implementation**:

- **Reusable Hate Speech Detection Framework**: Full Python codebase designed for extensibility beyond antisemitism detection. The framework can be adapted for any type of hate speech detection by:
  - Modifying `targeting.json` to specify different target subreddits relevant to the hate speech type
  - Updating search terms in `targeting.json` to reflect specific terminology and dog whistles
  - Modifying the detection prompt in `llm/prompts/detection_prompt.md` to focus on the specific hate speech category
  - Adjusting the output schema in `data/schemas/geminis_llm_schema.json` for different classification needs

**Core Pipeline Components**:

- `main.py` - Central pipeline orchestration with configurable stage execution
- `multi_threaded_gather.py` - Multi-threaded Reddit data collection with thread-aware rate limiting
- `data_processing.py` - Data transformation and conversation composition utilities
- `perspective_assessment.py` - Google Perspective API integration for toxicity scoring
- `gemini_assessment.py` - Google Gemini LLM integration for specialized hate speech detection
- `reddit_api.py` - Reddit API utilities and search functionality
- `utils.py` - Common utilities and Google Sheets integration

**API Integration Modules**:

- `llm/perspective_api.py` - Google Perspective API client with rate limiting and error handling
- `llm/gemini_api.py` - Google Gemini API client with structured output support
- `submodules/google_api/` - Google Sheets API integration utilities

**Configuration and Setup**:

- `targeting.json` - Comprehensive configuration file for targeting different hate speech types
- `requirements.txt` - Complete dependency specifications
- `.env.example` - Template for environment variable configuration
- `client_secrets.json.example` - Template for Google API credentials

### 1.3 Documentation Deliverables

**Technical Documentation**:

- **Pipeline Documentation** (`PIPELINE_DOCUMENTATION.md`): Comprehensive guide covering all pipeline stages, API integrations, configuration options, and troubleshooting procedures
- **README Documentation** (`README.md`): Quick start guide with installation instructions, basic usage examples, and project overview
- **API Documentation**: Detailed function documentation within code modules explaining parameters, return values, and usage examples

**Business Documentation**:

- **Technical Specification** (this document): Complete methodology explanation, architectural decisions, and system capabilities
- **Configuration Guide**: Detailed instructions for adapting the system to different hate speech detection scenarios
- **Results Interpretation Guide**: Documentation explaining how to interpret Perspective scores, Gemini assessments, and confidence levels

### 1.4 Data Access and Storage

**Google Sheets Integration**:

- **Real-time Data Access**: Live Google Sheets containing all collected and processed data with automatic updates
- **Collaborative Access**: Shared spreadsheets enabling team collaboration and real-time monitoring
- **Organized Data Sheets**: Separate sheets for posts, comments, perspectives, and gemini assessments

**Local Data Storage**:

- **Backup Files**: Complete local copies of all data in CSV and JSON formats
- **Error Logs**: Comprehensive logging files for debugging and system monitoring
- **Progress Tracking**: Detailed execution logs with timing and success metrics

### 1.5 Extensibility Features

**Framework Adaptability**:

- **Hate Speech Type Flexibility**: System designed to detect racism, xenophobia, homophobia, transphobia, or any other hate speech category through configuration changes only
- **Platform Extensibility**: Architecture allows integration with other social media platforms beyond Reddit by implementing new API modules
- **AI Model Flexibility**: Modular design supports substitution of different AI services (Claude, GPT, etc.) through configuration updates

**Scalability Components**:

- **Multi-threading Support**: Built-in parallel processing capabilities for handling larger datasets
- **Batch Processing**: Configurable batch sizes for optimal API usage and performance
- **Rate Limiting Framework**: Sophisticated rate limiting system adaptable to different API constraints

**Quality Assurance Deliverables**:

- **Error Handling Systems**: Comprehensive error recovery and logging mechanisms
- **Data Validation**: Input/output validation at each pipeline stage
- **Testing Framework**: Example test cases and validation procedures for system reliability

## 2. System Requirements & Dependencies

### 2.1 Required API Access

**Reddit API**:

- Client ID and Client Secret (Developer Application)
- Reddit username for API access

**Google APIs**:

- Perspective API key (Content Moderation)
- Gemini API access token (AI/ML)
- Google Cloud Console project ID
- Google Sheets API credentials

### 2.2 Python Dependencies

**Core Libraries**:

- `praw` - Reddit API wrapper
- `pandas` - Data manipulation and analysis
- `google-api-python-client` - Google APIs integration
- Additional utilities for logging, threading, and data processing

### 2.3 Configuration Files

**Required Files**:

- `targeting.json` - Search terms and target subreddits
- `client_secrets.json` - Google API credentials
- `.env` - Environment variables and API keys
- `llm/prompts/detection_prompt.md` - AI prompt template
- `data/schemas/geminis_llm_schema.json` - Output structure definition

## 3. Glossary of Project-Specific Terms

### 3.1 Core Data Structures

**Conversation**: A flattened representation of a Reddit post and all its associated comments, presented as a single string variable. The conversation maintains hierarchical structure through indentation, creating an unraveled tree where the root post is followed by all comments in their nested relationships. This format provides complete context for AI analysis while being compatible with text-based LLM APIs.

**Perspectives**: Toxicity scores retrieved from Google Perspective API, containing multiple attributes including toxicity, severe_toxicity, identity_attack, insult, profanity, threat, attack_on_author, attack_on_commenter, and inflammatory. These scores range from 0.0 to 1.0 and serve as the first-stage hate speech detection filter. Perspectives are used to reduce the volume of data processed by the more expensive Gemini API by pre-filtering potentially problematic content.

**Geminis**: Final anti-Semitism assessments generated by Google Gemini LLM. Each Gemini record contains: post_id, comment_id, user_id, subreddit, binary antisemitic classification, confidence score, detailed reasoning for the decision, severity assessment, and suggestions for future prompt modifications. Geminis represent the second-stage, specialized detection layer focused specifically on anti-Semitic content.

### 3.2 Specialized Processing Components

**Targeting Configuration**: JSON file (`targeting.json`) containing search terms, target subreddits, API configuration parameters, and Google Sheets integration settings. This file drives the data collection strategy and can be modified to target different types of hate speech by changing subreddits and search terms.

**Multi-threaded Gathering**: Parallel processing approach where each target subreddit is processed in a separate thread, allowing simultaneous data collection. Rate limiting considers that multiple threads are calling API endpoints simultaneously, with delays calculated per thread (0.6 seconds × number of threads for Reddit API) to prevent exceeding overall API quotas.

**Conversation Tree Flattening**: Process of converting Reddit's hierarchical post-comment structure into linear string format while preserving parent-child relationships through indentation levels. This enables LLM processing of complete conversation context.

### 3.3 Key Pipeline Functions

**`multi_threaded_gather()`**: Main orchestration function in `multi_threaded_gather.py` that spawns threads for each subreddit and coordinates the data collection process with thread-aware rate limiting.

**`search_subreddit_posts()`**: Core function in `reddit_api.py` that searches for posts within a specific subreddit using provided search terms, applying randomization to avoid predictable patterns and detection.

**`compose_conversations()`**: Critical function in `data_processing.py` that transforms separate posts and comments data into structured conversation threads, building the hierarchical tree structure with proper indentation for LLM consumption.

**`sort_conversations_by_score()`**: Function in `data_processing.py` that ranks conversations based on their maximum Perspective API toxicity scores, prioritizing high-risk content for Gemini analysis and optimizing processing order.

**`process_batch_perspective()`**: Function in `perspective_assessment.py` that sends batches of conversations to Google Perspective API for toxicity scoring, handling rate limiting and error recovery across multiple request types.

**`process_batch_gemini()`**: Function in `gemini_assessment.py` that processes conversations through Gemini LLM for anti-Semitism detection, using structured output schemas and adaptive prompt engineering.

### 3.4 Hate Speech Detection Terms

**Perspective Attributes**: Specific toxicity categories analyzed by Google Perspective API as first-stage filters:

- `TOXICITY`: General toxic behavior detection
- `SEVERE_TOXICITY`: Highly toxic content identification
- `IDENTITY_ATTACK`: Attacks on identity or demographic groups
- `INFLAMMATORY`: Content designed to provoke strong reactions
- `THREAT`: Threatening language detection
- `ATTACK_ON_AUTHOR`: Attacks directed at post authors
- `ATTACK_ON_COMMENTER`: Attacks directed at commenters

**Anti-Semitism Detection Schema**: Structured output format for Gemini API responses containing post identification, binary classification, confidence scoring, detailed reasoning, and prompt improvement suggestions specifically designed for anti-Semitic content detection.

**Search Term Randomization**: Technique of randomly selecting from available search terms to avoid predictable data collection patterns and potential detection by content moderators.

**Context-Aware Scoring**: LLM-based assessment that considers full conversation context rather than individual posts/comments in isolation, enabling detection of subtle and implicit hate speech.

### 3.5 Data Collection Specialization

**Lazy Object Handling**: Specialized processing of Reddit API objects that load data on-demand, using generator functions to efficiently handle large comment trees without memory exhaustion.

**Thread-Aware Rate Limiting**: Rate limiting system that accounts for multiple concurrent threads accessing the same API endpoints, calculating delays based on total thread count to prevent aggregate rate limit violations.

**Subreddit Targeting Strategy**: Methodology for identifying and monitoring specific Reddit communities known for hosting controversial or extremist content, configurable through the targeting JSON file.

**Conversation Composition**: Process of merging separate Reddit posts and comments into unified conversation strings suitable for LLM analysis, maintaining chronological order and reply relationships.

### 3.6 Reusable Framework Components

**Hate Speech Detection Framework**: Generalized pipeline architecture that can be adapted for different types of hate speech detection by modifying the targeting configuration and detection prompts without code changes.

**Adaptive Prompt Engineering**: System where AI-generated suggestions for prompt improvements are captured and can be integrated to enhance detection accuracy for evolving hate speech patterns.

**Modular API Integration**: Architecture allowing different AI services to be substituted in the detection pipeline by modifying configuration files rather than core code.

## 4. Executive Summary

This document outlines the design and implementation of an automated anti-Semitism detection system for Reddit content. The solution employs a multi-stage pipeline combining Reddit data collection, industry-standard hate speech detection, and advanced AI-powered anti-Semitism assessment to identify potentially harmful users and content.

## 5. Technical Architecture Overview

### 5.1 System Components

The pipeline consists of five integrated stages:

1. **Data Gathering** - Multi-threaded Reddit data collection via `multi_threaded_gather.py`
2. **Data Processing** - Conversation composition and structuring via `data_processing.py`
3. **Perspective API Assessment** - Industry-standard toxicity scoring via `perspective_assessment.py`
4. **Conversation Sorting** - Risk prioritization via `sort_conversations_by_score()` function
5. **Gemini LLM Assessment** - Advanced anti-Semitism detection via `gemini_assessment.py`

### 5.2 Technology Stack

- **Language**: Python 3.8+
- **APIs**: Reddit (PRAW), Google Perspective API, Google Gemini API
- **Data Storage**: Google Sheets, CSV files
- **Processing**: Pandas, multi-threading
- **AI/ML**: Google Gemini 2.5 Flash, Google Perspective API

## 6. Data Collection Methodology

### 6.1 Reddit API Selection Rationale

**Chosen Approach**: Official Reddit API (PRAW library)

**Alternative Approaches Considered**:

- Web scraping - Rejected due to legal/ToS concerns and brittleness
- JSON endpoints - Rejected due to unofficial status and potential instability

**Justification**:

- **Legal Compliance**: Adheres to Reddit's Terms of Service
- **Robustness**: Official API provides stable, documented interface
- **Efficiency**: Optimized for programmatic access with proper rate limiting
- **Production Ready**: Suitable for enterprise deployment

### 6.2 Target Identification Strategy

**Configuration-Driven Approach**:

- `targeting.json` file contains search terms and target subreddits
- Search terms identified using Grok AI for comprehensive coverage
- Combination of explicit and implicit anti-Semitic terminology
- Neutral terms included to avoid bias and ensure comprehensive coverage

**Multi-Threading Implementation**:

- Separate thread per subreddit for parallel processing
- Randomized search term selection to avoid predictable patterns
- Rate limiting (0.6s between requests) to respect API constraints

### 6.3 Data Collection Scope

**Content Types**:

- Reddit posts with full metadata
- Complete comment threads under each post
- User account information and posting history

**Data Fields Captured**:

- Post ID, title, content, author, subreddit, timestamp
- Comment ID, content, author, parent relationships
- Account metadata and posting patterns

## 7. Data Enrichment & Processing

### 7.1 Conversation Composition

**Challenge**: Reddit data exists as separate posts and comments requiring reconstruction into meaningful conversation threads.

**Solution**: Custom `compose_conversations()` function in `data_processing.py` that:

- Builds hierarchical comment trees from flat data structures
- Maintains parent-child relationships with proper indentation
- Creates complete conversation context for analysis
- Handles edge cases (deleted comments, missing parents)

**Benefits**:

- Provides full context for AI analysis
- Enables detection of subtle, context-dependent anti-Semitism
- Improves accuracy of threat assessment

### 7.2 Data Storage Strategy

**Primary Storage**: Google Sheets integration via `submodules/google_api/`

- Real-time data visibility and collaboration
- Built-in sharing and access control
- Easy integration with business workflows

**Secondary Storage**: Local CSV files

- Backup and offline processing capability
- Integration with data analysis tools
- Performance optimization for large datasets

## 8. Scoring Methodology

### 8.1 Two-Tier Assessment Approach

**Tier 1: Google Perspective API (Industry Standard Filter)**

- **Purpose**: Initial toxicity screening and baseline assessment
- **Attributes Analyzed**: Toxicity, Severe Toxicity, Identity Attack, Insult, Profanity, Threat, Inflammatory content
- **Benefits**: Established industry standard, high reliability, comprehensive toxicity detection
- **Limitations**: Not specifically trained for anti-Semitism, 20,000 character limit, 1 request/second rate limit

**Tier 2: Google Gemini LLM (Specialized Anti-Semitism Detection)**

- **Purpose**: Advanced anti-Semitism detection with contextual understanding
- **Model**: Gemini 2.5 Flash with structured output
- **Approach**: Custom prompt engineering for explicit and implicit anti-Semitism detection
- **Benefits**: Context-aware analysis, nuanced understanding, detailed explanations

### 8.2 Prompt Engineering Strategy

**Adaptive Prompt System**:

- Base prompt designed for comprehensive anti-Semitism detection in `llm/prompts/detection_prompt.md`
- Focus on implicit content (more prevalent on moderated platforms post-2020)
- Structured output schema for consistent results in `data/schemas/geminis_llm_schema.json`
- Self-improving system: AI suggests prompt modifications based on detected patterns

**Output Structure**:

- User ID, Post ID, Comment ID identification
- Confidence scoring (0-1 scale)
- Detailed reasoning for each assessment
- Severity classification
- Suggested prompt improvements for future iterations

## 9. Technical Implementation Details

### 9.1 Rate Limiting & API Management

**Reddit API**: 0.6 seconds between requests multiplied by the number of threads
**Perspective API**: 1.1 seconds between requests via `llm/perspective_api.py`
**Gemini API**: 1.1 seconds between requests via `llm/gemini_api.py`

**Error Handling**:

- Comprehensive logging system with detailed error context via `logs/` directory
- Automatic retry logic with exponential backoff
- Graceful degradation for API failures
- Progress tracking and recovery capabilities

### 9.2 Scalability Considerations

**Multi-Threading**:

- Parallel processing of different subreddits via `multi_threaded_gather.py`
- Thread-safe logging and data storage
- Configurable thread pools based on API limits

**Batch Processing**:

- Configurable batch sizes for API calls
- Memory-efficient processing of large datasets
- Progress monitoring for long-running operations

### 9.3 Resource Optimization

**Context Management**:

- Dynamic conversation length optimization
- Token usage tracking and optimization
- Memory-efficient data structures

**Cost Management**:

- Free-tier API usage optimization
- Intelligent conversation prioritization
- Caching strategies to minimize redundant API calls

## 10. Edge Cases & Error Handling

### 10.1 Data Quality Issues

**Missing Data**:

- Deleted posts and comments handling
- Private/suspended account management
- API timeout and failure recovery

**Content Limitations**:

- Character limits for different APIs
- Rate limiting across multiple services
- Token budget management for LLM APIs

## 11. Performance Metrics & Limitations

### 11.1 Current System Limitations

**Budget Constraints**:

- Free-tier API usage limiting processing speed
- Google Perspective API: 20,000 characters per request, 1 request/second
- Gemini API: 1,000 requests/day, 250,000 tokens/day

**Processing Speed**:

- Sequential conversation processing due to rate limits
- Reduced parallelization to stay within quotas

### 11.2 Performance Optimizations

**Efficiency Measures**:

- Conversation prioritization by toxicity scores via `sort_conversations_by_score()`
- Batch processing where possible
- Generator-based data processing to reduce memory usage and make use of PRAW lazy objects
- Intelligent caching and data reuse

## 12. Future Enhancement Roadmap

### 12.1 Short-term Improvements

**Performance Optimization**:

- Implement caching for reduced API usage
- Optimize batch processing for better throughput
- Add parallel processing capabilities within API limits

**Feature Enhancements**:

- Real-time monitoring dashboard
- Advanced filtering and search capabilities
- Automated report generation

### 12.2 Long-term Scaling

**Infrastructure Scaling**:

- Cloud deployment for enterprise scale
- Database integration for large-scale data management
- Distributed processing architecture

**AI/ML Improvements**:

- Custom model training for anti-Semitism detection
- Integration with additional AI services
- Continuous learning and model improvement

## 13. Conclusion

This anti-Semitism detection pipeline represents a comprehensive solution combining industry-standard tools with advanced AI capabilities. The system successfully addresses the core business requirements while maintaining scalability, accuracy, and ethical considerations. The modular architecture allows for future enhancements and adaptation to evolving requirements in hate speech detection and content moderation.

The implementation demonstrates practical application of modern AI technologies for social good, providing a foundation for larger-scale deployment in content moderation and community safety applications.
