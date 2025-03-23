<?php
// Security check - you can use a fixed token or adjust as needed
$expected_token = "your_secret_token_here";
$submitted_token = isset($_POST['token']) ? $_POST['token'] : '';

if ($submitted_token !== $expected_token) {
    die("Unauthorized access");
}

// Get data from POST request
$subject = isset($_POST['subject']) ? $_POST['subject'] : 'Property Update';
$message = isset($_POST['message']) ? $_POST['message'] : 'No message provided';

// Your email configuration
$to = "your-email@example.com";
$headers = "MIME-Version: 1.0" . "\r\n";
$headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
$headers .= "From: Property Monitor <noreply@yourdomain.com>" . "\r\n";

// Send email
$success = mail($to, $subject, $message, $headers);

// Return result
if ($success) {
    echo json_encode(['status' => 'success', 'message' => 'Email sent successfully']);
} else {
    echo json_encode(['status' => 'error', 'message' => 'Failed to send email']);
}
?>
