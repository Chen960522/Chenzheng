// Quote Request Page Logic

let currentQuoteId = null;

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('quoteRequestForm');
    const fileInput = document.getElementById('configFile');
    const cancelBtn = document.getElementById('cancelBtn');

    // File upload handler
    fileInput.addEventListener('change', (e) => {
        const fileName = e.target.files[0]?.name || '';
        document.getElementById('fileName').textContent = fileName;

        // Read file content
        if (e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = (event) => {
                document.getElementById('configText').value = event.target.result;
            };
            reader.readAsText(e.target.files[0]);
        }
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleQuoteRequest();
    });

    // Cancel button
    cancelBtn.addEventListener('click', () => {
        window.location.href = 'dashboard.html';
    });
});

async function handleQuoteRequest() {
    const configText = document.getElementById('configText').value.trim();
    const region = document.getElementById('region').value;
    const pricingModel = document.getElementById('pricingModel').value;
    const notes = document.getElementById('notes').value.trim();
    const errorDiv = document.getElementById('errorMessage');

    // Validation
    if (!configText) {
        errorDiv.textContent = 'Please enter a configuration or upload a file';
        errorDiv.style.display = 'block';
        return;
    }

    errorDiv.style.display = 'none';

    // Show processing status
    document.getElementById('quoteRequestForm').style.display = 'none';
    document.getElementById('processingStatus').style.display = 'block';

    try {
        // Create quote request
        const quoteData = {
            configuration: configText,
            region: region,
            pricing_model: pricingModel,
            notes: notes || null
        };

        const response = await api.createQuote(quoteData);
        currentQuoteId = response.quote_id;

        // Connect WebSocket for real-time updates
        wsClient.connect(currentQuoteId);
        wsClient.onMessage(handleStatusUpdate);

        // Initial status
        updateStatus('Initializing...', 10);
    } catch (error) {
        console.error('Failed to create quote:', error);
        errorDiv.textContent = error.message || 'Failed to create quote';
        errorDiv.style.display = 'block';
        document.getElementById('quoteRequestForm').style.display = 'block';
        document.getElementById('processingStatus').style.display = 'none';
    }
}

function handleStatusUpdate(data) {
    console.log('Status update:', data);

    if (data.type === 'progress') {
        updateStatus(data.message, data.progress);
    } else if (data.type === 'complete') {
        updateStatus('Quote generated successfully!', 100);
        setTimeout(() => {
            wsClient.disconnect();
            window.location.href = `quote-result.html?id=${currentQuoteId}`;
        }, 1000);
    } else if (data.type === 'error') {
        updateStatus(`Error: ${data.message}`, 0);
        setTimeout(() => {
            wsClient.disconnect();
            document.getElementById('quoteRequestForm').style.display = 'block';
            document.getElementById('processingStatus').style.display = 'none';
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = data.message;
            errorDiv.style.display = 'block';
        }, 2000);
    }
}

function updateStatus(message, progress) {
    const progressFill = document.getElementById('progressFill');
    const statusMessages = document.getElementById('statusMessages');

    progressFill.style.width = `${progress}%`;

    const messageEl = document.createElement('div');
    messageEl.className = 'status-message';
    messageEl.textContent = message;
    statusMessages.appendChild(messageEl);

    // Scroll to bottom
    statusMessages.scrollTop = statusMessages.scrollHeight;
}
