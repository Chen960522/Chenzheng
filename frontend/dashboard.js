// Dashboard Page Logic

document.addEventListener('DOMContentLoaded', async () => {
    await loadRecentQuotes();
});

async function loadRecentQuotes() {
    const listEl = document.getElementById('recentQuotesList');
    
    try {
        const quotes = await api.getQuoteHistory(5, 0);
        
        if (quotes.length === 0) {
            listEl.innerHTML = `
                <div class="empty-state">
                    <p data-i18n="dashboard.noQuotes">No quotes yet</p>
                    <a href="quote-request.html" class="btn btn-primary" data-i18n="dashboard.createFirst">Create Your First Quote</a>
                </div>
            `;
            updateTranslations();
            return;
        }

        listEl.innerHTML = quotes.map(quote => createQuoteCard(quote)).join('');
        updateTranslations();
    } catch (error) {
        console.error('Failed to load recent quotes:', error);
        listEl.innerHTML = `
            <div class="error-message" data-i18n="common.loadError">Failed to load quotes</div>
        `;
        updateTranslations();
    }
}

function createQuoteCard(quote) {
    const createdDate = new Date(quote.created_at).toLocaleDateString();
    const statusClass = `status-${quote.status}`;
    
    return `
        <div class="quote-card">
            <div class="quote-info">
                <h4>${quote.quote_id}</h4>
                <div class="quote-meta">
                    <span>${createdDate}</span>
                    <span class="status-badge ${statusClass}">${quote.status}</span>
                    <span class="price">$${quote.total_monthly_cost.toFixed(2)}/mo</span>
                </div>
            </div>
            <div class="quote-actions">
                <a href="quote-result.html?id=${quote.quote_id}" class="btn btn-secondary" data-i18n="common.view">View</a>
            </div>
        </div>
    `;
}
