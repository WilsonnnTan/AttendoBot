# Discord Attendance Bot — Technical Documentation

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Docker Setup](#docker-setup)
- [Environment Configuration](#environment-configuration)
- [Database Schema](#database-schema)
- [Business Logic](#business-logic)
- [Deployment](#deployment)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [License](#license)

---

## Architecture Overview

The Discord Attendance Bot is a modular Python application built on `discord.py`, using Google Forms for attendance collection and Supabase (via direct HTTP requests using httpx) for persistent storage. The bot restricts configuration commands to server admins for security. Concurrency for both database and Google Form operations is managed using asyncio semaphores, ensuring stability even under high load.

**Key Components:**
- `app.py`: Bot entry point, event loop, and core command registration.
- `utils/GoogleForm.py`: Google Form integration, including URL extraction (performed when adding a form URL), data fetching, and attendance submission logic.
- `utils/database.py`: Async database handler for all Supabase CRUD operations, using httpx and concurrency limits.

---

## Local Development Setup

You can run the Discord Attendance Bot locally using Python and a virtual environment. This is recommended for development and testing.

### 1. Clone the repository
```bash
git clone https://github.com/WilsonnnTan/AttendoBot.git
cd AttendoBot
```

### 2. Create and activate a virtual environment
#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```
#### Linux/MacOS
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and edit it with your credentials.

### 5. Initialize the database (if needed)
```bash
alembic upgrade head
```

### 6. Run the bot
```bash
python app.py
```

---

## Docker Setup

### 1. Build the Docker image
```bash
docker build -t AttendoBot .
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and edit it with your credentials, or set variables in your deployment environment.

### 3. Run the bot container
```bash
docker run --env-file .env --name AttendoBot AttendoBot
```

### 4. (Optional) Run as a background service
```bash
docker run -d --env-file .env --name AttendoBot AttendoBot
```

### 5. Database Migrations
If you need to run Alembic migrations inside the container:
```bash
docker run --rm --env-file .env AttendoBot alembic upgrade head
```

---

## Environment Configuration

Create a `.env` file based on `.env.example`:

```env
DISCORD_TOKEN="YOUR_DISCORD_TOKEN"
SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY="YOUR_SUPABASE_KEY"
DATABASE_MIGRATION_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres"
LOG_LEVEL=WARNING
GOOGLEFORM_MAX_CONCURRENCY="10"
SUPABASE_MAX_CONCURRENCY="10"
```

---

## Database Schema

### Tables
- **guilds**: Stores guild (server) configuration, including Google Form URL, entry field ID, and attendance window.
- **attendances**: Records each user's attendance per guild.
- **Timezone**: Stores timezone offset per guild. Default is UTC+7 (Jakarta) if not set.

Table creation and migrations are managed through Supabase and SQL scripts, not SQLAlchemy.

---

## Business Logic

- **Attendance Marking**:  
  Users mark attendance with `/hadir`. The bot checks the configured time window and prevents duplicate attendance for the same day. If no attendance window is set, users can mark attendance anytime.

- **Google Form Integration**:  
  Admins configure a Google Form URL. The bot extracts field IDs, submits attendance, and validates URLs.

- **Admin Controls**:  
  Only users with `administrator` or `manage_guild` permissions can configure the bot.

- **Timezone & Attendance Window**:  
  Attendance is only accepted within the configured window and timezone. If not set, attendance can be marked anytime and UTC+7 (Jakarta) is used as the default timezone.

---

## Deployment

- **Local:**  
  see [Local Development Setup](#local-development-setup).

- **Docker:**  
  See [Docker Setup](#docker-setup).

---

## Troubleshooting & FAQ

**Q: The bot doesn't respond to commands.**  
A: Check that the bot is running, has the correct token, and has permission to read/send messages in your Discord server.

**Q: Attendance is denied even during the correct window.**  
A: Verify your server timezone and attendance window configuration with `/show_timezone` and `/show_attendance_time`.

**Q: How do I reset the attendance window or form URL?**  
A: Use `/delete_attendance_time` or `/delete_gform_url` as an admin.

**Q: How do I migrate the database?**  
A: Use `alembic upgrade head` locally, or run the migration command inside your Docker container as shown above.

---

## License

This project is licensed under the terms specified in the LICENSE file.

---

For further questions or contributions, please submit an issue or pull request on GitHub.
