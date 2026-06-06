"""
Email utilities for sending notifications
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_file_shared_email(recipient_email, file_name, shared_by_name, shared_by_email, file_id, role):
    """
    Send email notification when a file is shared with someone
    
    Args:
        recipient_email: Email of the person receiving the share
        file_name: Name of the shared file
        shared_by_name: Name of the person sharing
        shared_by_email: Email of the person sharing
        file_id: ID of the file
        role: Permission role (reader, commenter, writer)
    """
    subject = f"{shared_by_name} shared '{file_name}' with you"
    
    # Create email context
    context = {
        'recipient_email': recipient_email,
        'file_name': file_name,
        'shared_by_name': shared_by_name,
        'shared_by_email': shared_by_email,
        'role': role,
        'dashboard_url': f"{settings.SITE_URL}/project/files.html",
        'file_id': file_id,
    }
    
    # Try to render HTML template, fallback to plain text
    try:
        html_message = render_to_string('file_shared_email.html', context)
        text_message = render_to_string('file_shared_email.txt', context)
    except:
        # Fallback plain text message
        html_message = f"""
        <h2>File Shared with You</h2>
        <p>{shared_by_name} ({shared_by_email}) has shared a file with you:</p>
        <p><strong>File:</strong> {file_name}</p>
        <p><strong>Permission:</strong> {role}</p>
        <p><a href="{context['dashboard_url']}">View in CloudVault</a></p>
        """
        text_message = f"""
File Shared with You

{shared_by_name} ({shared_by_email}) has shared a file with you:

File: {file_name}
Permission: {role}

View in CloudVault: {context['dashboard_url']}
        """
    
    # Send email
    try:
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {str(e)}")
        return False


def send_file_unshared_email(recipient_email, file_name, unshared_by_name):
    """
    Send email notification when a file share is revoked
    
    Args:
        recipient_email: Email of the person whose access was revoked
        file_name: Name of the file
        unshared_by_name: Name of the person revoking access
    """
    subject = f"Access to '{file_name}' has been revoked"
    
    context = {
        'recipient_email': recipient_email,
        'file_name': file_name,
        'unshared_by_name': unshared_by_name,
        'dashboard_url': f"{settings.SITE_URL}/project/files.html",
    }
    
    html_message = f"""
    <h2>File Access Revoked</h2>
    <p>{unshared_by_name} has revoked your access to the following file:</p>
    <p><strong>File:</strong> {file_name}</p>
    <p>You will no longer be able to access this file.</p>
    """
    
    text_message = f"""
File Access Revoked

{unshared_by_name} has revoked your access to the following file:

File: {file_name}

You will no longer be able to access this file.
    """
    
    try:
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {str(e)}")
        return False


def send_share_link_email(recipient_email, file_name, shared_by_name, share_link_url, message=None):
    """
    Send email with a public share link
    
    Args:
        recipient_email: Email to send to
        file_name: Name of the shared file
        shared_by_name: Name of person sharing
        share_link_url: The public share link URL
        message: Optional custom message
    """
    subject = f"{shared_by_name} shared a file link with you: {file_name}"
    
    context = {
        'recipient_email': recipient_email,
        'file_name': file_name,
        'shared_by_name': shared_by_name,
        'share_link_url': share_link_url,
        'message': message,
    }
    
    html_message = f"""
    <h2>File Shared via Link</h2>
    <p>{shared_by_name} has shared a file with you:</p>
    <p><strong>File:</strong> {file_name}</p>
    {f'<p><strong>Message:</strong> {message}</p>' if message else ''}
    <p><a href="{share_link_url}">Access the file</a></p>
    """
    
    text_message = f"""
File Shared via Link

{shared_by_name} has shared a file with you:

File: {file_name}
{f'Message: {message}' if message else ''}

Access the file: {share_link_url}
    """
    
    try:
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {str(e)}")
        return False
