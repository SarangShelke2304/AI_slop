---
description: Steps to deploy the AI Slop pipeline to an Amazon Linux 2023 EC2 instance
---

### 1. SSH into your EC2 Instance
Open your terminal on Windows and run:
```bash
ssh -i "your-key.pem" ec2-user@your-instance-public-dns
```

### 2. Update System and Install Dependencies
Once inside the EC2, run these commands:
```bash
# Update system
sudo dnf update -y

# Install Python 3.11 and Git
sudo dnf install python3.11 git -y

# Tell Poetry to use Python 3.11
cd AI_slop
poetry env use python3.11

# Install FFmpeg
sudo dnf install ffmpeg -y

# Install Poetry
curl -sSL https://install.python-poetry.org | python3.11 -
export PATH="$HOME/.local/bin:$PATH"
```

### 3. Clone the Repository
```bash
git clone https://github.com/SarangShelke2304/AI_slop.git
cd AI_slop
```

### 4. Install Project Dependencies
```bash
poetry install
```

### 5. Setup Environment Variables
1. Copy the example env: `cp .env.example .env`
2. Edit the `.env`: `nano .env`
   - Fill in your `GROQ_API_KEY`, `OPENAI_API_KEY`.
   - Update `DATABASE_URL` with your Supabase link.
   - **CRITICAL**: Set `FFMPEG_PATH=` (leave it empty) so it uses the system FFmpeg.
   - Update file paths like `GOOGLE_OAUTH_CREDENTIALS_PATH` to `/home/ec2-user/AI_slop/oauth-credentials.json`.

### 6. Transfer Secret Files (From your Local Windows Machine)
Open a **new** terminal on your Windows PC (not on SSH) and run:
```bash
scp -i "your-key.pem" D:\ai_slop\token.json ec2-user@your-instance-public-dns:/home/ec2-user/AI_slop/
scp -i "your-key.pem" D:\ai_slop\oauth-credentials.json ec2-user@your-instance-public-dns:/home/ec2-user/AI_slop/
```

### 7. Run the Pipeline
Back in your SSH terminal:
```bash
poetry run python src/main.py
```
