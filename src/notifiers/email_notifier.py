
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from pathlib import Path
from typing import List, Dict, Optional

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import with_retry

class EmailNotifier:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.sender = settings.SENDER_EMAIL or self.username
        self.recipient = settings.NOTIFICATION_EMAIL
        
        self.enabled = all([
            self.smtp_server, 
            self.port_is_valid(),
            self.username, 
            self.password, 
            self.recipient,
            not settings.TEST_MODE
        ])
        
        if not self.enabled and not settings.TEST_MODE:
            logger.warning("Email notifications disabled: Missing SMTP config.")

    def port_is_valid(self):
        return self.smtp_port and self.smtp_port > 0

    @with_retry(max_attempts=3)
    def _send_email(self, subject: str, body_html: str, attachments: List[str] = None):
        """
        Send email via SMTP with HTML body and attachments.
        """
        if not self.enabled:
            logger.info(f"Email skipped (disabled/test mode): {subject}")
            return

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = self.recipient

        msg.attach(MIMEText(body_html, 'html'))

        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if path.exists():
                    with open(path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=path.name)
                        part['Content-Disposition'] = f'attachment; filename="{path.name}"'
                        msg.attach(part)

        try:
            # Connect to valid SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls() # Secure the connection
                server.login(self.username, self.password)
                server.send_message(msg)
                
            logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def send_run_summary(self, 
                       stories_count: int, 
                       videos_created: int, 
                       uploads_success: int, 
                       errors: List[str]):
        """
        Send daily/run summary email.
        """
        subject = f"AI Slop Pipeline Summary - {videos_created} Videos Created"
        
        error_html = ""
        if errors:
            error_html = "<h3>Errors Encountered:</h3><ul>" + \
                         "".join([f"<li style='color:red'>{e}</li>" for e in errors]) + \
                         "</ul>"
        
        body = f"""
        <h2>Pipeline Run Completed</h2>
        <ul>
            <li>Stories Scraped: {stories_count}</li>
            <li>Videos Created: {videos_created}</li>
            <li>YouTube Uploads: {uploads_success}</li>
        </ul>
        {error_html}
        <p>Check logs for details.</p>
        """
        self._send_email(subject, body)

    def send_instagram_upload_request(self, video_path: str, title: str, download_link: str, hashtags: str):
        """
        Send email with link and details for manual Instagram upload.
        """
        subject = f"READY FOR INSTAGRAM: {title}"
        
        body = f"""
        <h2>New Video Ready for Instagram</h2>
        <p><b>Title:</b> {title}</p>
        <p><b>Download Link:</b> <a href="{download_link}">Click to Download</a></p>
        <br>
        <h3>Suggested Caption:</h3>
        <pre>{title}\n\n{hashtags}</pre>
        <br>
        <p><i>Note: Download link expires if valid permissions are not set.</i></p>
        """
        
        # We don't attach the video file itself as it might be too large (20MB+) for email.
        # Links are better.
        self._send_email(subject, body)

    def send_error_alert(self, error_msg: str, context: str):
        """
        Send critical error alert.
        """
        subject = f"CRITICAL ERROR: Pipeline Failed"
        body = f"""
        <h2 style='color:red'>Critical Error</h2>
        <p><b>Context:</b> {context}</p>
        <pre>{error_msg}</pre>
        """
        self._send_email(subject, body)

    def send_email(self, subject: str, message: str):
        """
        Generic email sender.
        """
        body = f"<pre>{message}</pre>"
        self._send_email(subject, body)

    def send_progress_update(self, current: int, total: int, stage: str):
        """
        Send specific progress update.
        """
        percentage = int((current / total) * 100)
        # Send only at specific intervals to avoid spam 
        # (Already handled by caller logic, but we can double check)
        
        subject = f"Progress {percentage}% - {stage}"
        body = f"""
        <h2>Job Progress: {percentage}%</h2>
        <p><b>Stage:</b> {stage}</p>
        <p>{current} / {total} items processed.</p>
        """
        self._send_email(subject, body)


    def send_completion_report(self, videos: List[Dict]):
        """
        Send final report with links to all generated videos.
        """
        subject = f"Pipeline Complete - {len(videos)} Videos Ready"
        
        video_list_html = ""
        for v in videos:
            video_list_html += f"""
            <li>
                <b>{v.get('title', 'Unknown')}</b><br>
                <a href="{v.get('download_url')}">Download Video</a><br>
                <small>{v.get('hashtags')}</small>
            </li><br>
            """
            
        body = f"""
        <h2>Pipeline Execution Finished</h2>
        <p>Generated {len(videos)} videos successfully.</p>
        <ul>
            {video_list_html}
        </ul>
        """
        self._send_email(subject, body)

# Global instance
email_notifier = EmailNotifier()
