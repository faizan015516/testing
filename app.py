# Updated app.py

import os
import json

import io  # Moved here

# Other imports
# ... (rest of your existing imports)

# Code starts ...

# Other code ...

# Removed unused variable `ext`

# XHR response handling section
function handleUploadResponse(response) {
    if (response.status >= 200 && response.status < 300) {
        // Success handling
        return response.json();
    } else {
        // Error handling
        return response.json().then((errorData) => {
            console.error('Error response:', errorData);
            throw new Error('Upload failed: ' + errorData.message);
        });
    }
}

# Code continues ...