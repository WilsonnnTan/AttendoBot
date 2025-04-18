# Technical Documentation

## Project Structure

```
Discord-Attendance-Bot/
├── .env                # Environment variables (not committed)
├── .env.example        # Example environment config
├── Dockerfile          # Docker configuration for deployment
├── LICENSE             # License file
├── README.md           # Main documentation and setup instructions
├── DOCUMENTATION.md    # Technical documentation (this file)
├── alembic.ini         # Alembic configuration for database migrations
├── app.py              # Main application entry point
├── requirements.txt    # Python dependencies
├── migration/          # Database migration scripts
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── schemas/
│   └── models.py       # SQLAlchemy database models
└── utils/
    ├── GoogleForm.py   # Google Form handling and bot commands
    ├── database.py     # Database operations
    └── __init__.py
```

## Core Components

### 1. Database Models (`schemas/models.py`)

#### Guild Model
```python
class Guild(Base):
    __tablename__ = 'guilds'
    guild_id = Column(BigInteger, primary_key=True)
    form_url = Column(Text, nullable=True)
    day = Column(Integer, nullable=True)
    start_hour = Column(Integer, nullable=True)
    start_minute = Column(Integer, nullable=True)
    end_hour = Column(Integer, nullable=True)
    end_minute = Column(Integer, nullable=True)
```
Stores Discord server (guild) configurations including:
- Google Form URL
- Attendance window day and time

#### Attendance Model
```python
class Attendance(Base):
    __tablename__ = 'attendances'
    guild_id = Column(BigInteger, ForeignKey('guilds.guild_id'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    form_url = Column(Text, nullable=True)
    __table_args__ = (PrimaryKeyConstraint('guild_id', 'user_id'),)
```
Records user attendance with:
- Guild and user IDs
- Timestamp of attendance
- Form URL used

#### Timezone Model
```python
class Timezone(Base):
    __tablename__ = 'Timezone'
    guild_id = Column(BigInteger, ForeignKey('guilds.guild_id'), primary_key=True)
    time_delta = Column(Integer, nullable=True)
```
Stores timezone configuration for each guild.

### 2. Google Form Handler (`utils/GoogleForm.py`)

#### GoogleForm_Url_Handler Class
Handles Google Form interactions:

- `extract_urls(url: str) -> tuple[str, str]`
  - Extracts viewform and formResponse URLs
  - Handles both full and shortened (forms.gle) URLs
  - Returns `(view_url, post_url)` tuple

- `submit_response(post_url: str, data: dict) -> bool`
  - Submits form data to Google Forms
  - Returns success status

- `fetch_form_data(view_url: str) -> dict`
  - Retrieves form configuration data
  - Extracts form field IDs

- `get_entry_ids(data: dict) -> iter`
  - Recursively finds form field IDs
  - Used to identify name field for attendance

#### GoogleFormManager Class (Discord Commands)

Admin Commands:
1. Form Management:
   - `!add_gform_url <link>` - Configure form URL
   - `!delete_gform_url` - Remove form URL
   - `!list_gform_url` - Show current URL

2. Attendance Window:
   - `!set_attendance_time <day>/<HH:MM>-<HH:MM>`
   - `!show_attendance_time`
   - `!delete_attendance_time`

3. Timezone Management:
   - `!set_timezone <offset>` (UTC-12 to UTC+14)
   - `!show_timezone`

User Commands:
- `!hadir` - Mark attendance

### 3. Main Application (`app.py`)

Core functionality:
1. Bot initialization with required intents
2. Attendance command (`!hadir`) implementation:
   - Validates time window
   - Checks previous attendance
   - Submits to Google Form
   - Provides user feedback

### 4. Database Operations (`utils/database.py`)

Key operations:
- Guild configuration CRUD
- Attendance tracking
- Timezone management
- Time window validation

## Attendance Flow

1. User types `!hadir`
2. Bot checks:
   - Guild has configured form URL
   - Current time is within attendance window
   - User hasn't already marked attendance

3. If checks pass:
   - Extracts form URLs
   - Fetches form configuration
   - Submits user's display name
   - Records attendance in database
   - Confirms success to user

## Security Features

1. Admin-only commands:
   - Requires administrator or manage_guild permission
   - Protected configuration commands

2. Form URL validation:
   - Validates Google Form URLs
   - Handles URL redirection safely

3. Time window enforcement:
   - Strict time window validation
   - Timezone-aware checks

## Error Handling

- Command errors logged with timestamps
- User-friendly error messages
- Failed form submissions tracked
- Database transaction safety

## Dependencies

Major dependencies:
- discord.py - Discord API wrapper
- SQLAlchemy - Database ORM
- alembic - Database migrations
- python-dotenv - Environment configuration
- requests - HTTP client for form submission
- pytz - Timezone handling
