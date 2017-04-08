# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText

# Open a plain text file for reading.  For this example, assume that
# the text file contains only ASCII characters.
with open('./output/param_log.don') as fp:
        # Create a text/plain message
    a = 'Running Program Finished!\n\n' + fp.read()
    msg = MIMEText(a)

# me == the sender's email address
# you == the recipient's email address
msg['Subject'] = 'Running Program Finished'
msg['From'] = "liyubing05@hotmail.com"
msg['To'] = "liyubing38@gmail.com"

# Send the message via our own SMTP server.
try:
    s = smtplib.SMTP("smtp-mail.outlook.com", 587)
    s.ehlo()
    s.starttls()
    s.login('liyubing05@hotmail.com', 'shzzlyb38')
    s.send_message(msg)
    s.quit()
    print("Successfully sent email")
except smtplib.SMTPException:
    print("Error: unable to send email")
