// Quote Result Page Logic

let currentQuote = null;

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const quoteId = urlParams.get('id');

    if (!quoteId) {
        window.location.href = 'dashboard.html';
        return;
    }

    await loadQuote(quoteId);
    setupEventHandlers(quoteId);
});

async function loadQuote(quoteId) {
    const contentEl = document.getElementById('quoteContent');

    try {
        currentQuote = await api.getQuote(quoteId);
        displayQuote(currentQuote);
    } catch (error) {
        console.error('Failed to load quote:', error);
        contentEl.innerHTML = `
            <div class="error-message">Failed to load quote: ${error.message}</div>
        `;
    }
}

function displayQuote(quote) {
    // Hide loading
    document.getElementById('quoteContent').style.display = 'none';

    // Show summary
    const summaryEl = document.getElementById('quoteSummary');
    summaryEl.style.display = 'block';
    document.getElementById('quoteId').textContent = quote.quote_id;
    document.getElementById('createdAt').textContent = new Date(quote.created_at).toLocaleString();
    document.getElementById('region').textContent = quote.region || 'N/A';
    document.getElementById('monthlyTotal').textContent = `$${quote.total_monthly_cost.toFixed(2)}`;
    document.getElementById('annualTotal').textContent = `$${quote.total_annual_cost.toFixed(2)}`;

    // Show service mappings
    if (quote.aws_services && quote.aws_services.length > 0) {
        const mappingsEl = document.getElementById('serviceMappings');
        mappingsEl.style.display = 'block';
        
        const mappingsList = document.getElementById('mappingsList');
        mappingsList.innerHTML = quote.aws_services.map(mapping => createMappingCard(mapping)).join('');
    }

    // Show pricing breakdown
    if (quote.pricing_results && quote.pricing_results.length > 0) {
        const breakdownEl = document.getElementById('pricingBreakdown');
        breakdownEl.style.display = 'block';
        
        const breakdownTable = document.getElementById('breakdownTable');
        breakdownTable.innerHTML = createBreakdownTable(quote.pricing_results);
    }

    // Show notes
    if (quote.notes) {
        const notesEl = document.getElementById('quoteNotes');
        notesEl.style.display = 'block';
        document.getElementById('notesContent').textContent = quote.notes;
    }

    updateTranslations();
}

function createMappingCard(mapping) {
    const originalService = mapping.original_service || 'Unknown';
    const awsService = mapping.aws_service || 'Unknown';
    const explanation = mapping.explanation || 'No explanation available';

    return `
        <div class="mapping-card">
            <div class="mapping-header">
                <div>
                    <strong>${originalService}</strong>
                    <p style="color: var(--text-light); font-size: 14px; margin-top: 5px;">
                        ${mapping.provider || 'Unknown Provider'}
                    </p>
                </div>
                <div class="mapping-arrow">→</div>
                <div>
                    <strong>${awsService}</strong>
                    <p style="color: var(--text-light); font-size: 14px; margin-top: 5px;">
                        ${mapping.aws_service_type || 'N/A'}
                    </p>
                </div>
            </div>
            <p style="color: var(--text-light); font-size: 14px; margin-top: 10px;">
                ${explanation}
            </p>
        </div>
    `;
}

function createBreakdownTable(pricingResults) {
    const rows = pricingResults.map(result => {
        const service = result.service || 'Unknown';
        const monthly = result.monthly_cost || 0;
        const annual = result.annual_cost || 0;
        const model = result.pricing_model || 'on-demand';

        return `
            <tr>
                <td>${service}</td>
                <td>${model}</td>
                <td>$${monthly.toFixed(2)}</td>
                <td>$${annual.toFixed(2)}</td>
            </tr>
        `;
    }).join('');

    return `
        <table>
            <thead>
                <tr>
                    <th data-i18n="result.service">Service</th>
                    <th data-i18n="result.pricingModel">Pricing Model</th>
                    <th data-i18n="result.monthly">Monthly Cost</th>
                    <th data-i18n="result.annual">Annual Cost</th>
                </tr>
            </thead>
            <tbody>
                ${rows}
            </tbody>
        </table>
    `;
}

function setupEventHandlers(quoteId) {
    // Download buttons
    document.getElementById('downloadPdfBtn').addEventListener('click', async () => {
        try {
            await api.downloadQuote(quoteId, 'pdf');
        } catch (error) {
            alert('Failed to download PDF: ' + error.message);
        }
    });

    document.getElementById('downloadExcelBtn').addEventListener('click', async () => {
        try {
            await api.downloadQuote(quoteId, 'excel');
        } catch (error) {
            alert('Failed to download Excel: ' + error.message);
        }
    });

    document.getElementById('downloadJsonBtn').addEventListener('click', async () => {
        try {
            await api.downloadQuote(quoteId, 'json');
        } catch (error) {
            alert('Failed to download JSON: ' + error.message);
        }
    });

    // Navigation buttons
    document.getElementById('backBtn').addEventListener('click', () => {
        window.history.back();
    });

    document.getElementById('newQuoteBtn').addEventListener('click', () => {
        window.location.href = 'quote-request.html';
    });
}
