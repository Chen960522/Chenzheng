// Quote History Page Logic

let allQuotes = [];
let quoteToDelete = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadQuoteHistory();
    setupEventHandlers();
});

async function loadQuoteHistory() {
    const listEl = document.getElementById('historyList');
    const emptyState = document.getElementById('emptyState');

    try {
        allQuotes = await api.getQuoteHistory(100, 0);

        if (allQuotes.length === 0) {
            listEl.style.display = 'none';
            emptyState.style.display = 'block';
            updateTranslations();
            return;
        }

        displayQuotes(allQuotes);
    } catch (error) {
        console.error('Failed to load quote history:', error);
        listEl.innerHTML = `
            <div class="error-message">Failed to load quote history: ${error.message}</div>
        `;
    }
}

function displayQuotes(quotes) {
    const listEl = document.getElementById('historyList');
    const emptyState = document.getElementById('emptyState');

    if (quotes.length === 0) {
        listEl.style.display = 'none';
        emptyState.style.display = 'block';
        updateTranslations();
        return;
    }

    listEl.style.display = 'grid';
    emptyState.style.display = 'none';

    listEl.innerHTML = quotes.map(quote => createQuoteCard(quote)).join('');
    updateTranslations();

    // Add event listeners to delete buttons
    document.querySelectorAll('.delete-quote-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const quoteId = e.target.dataset.quoteId;
            showDeleteModal(quoteId);
        });
    });
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
                <button class="btn btn-danger delete-quote-btn" data-quote-id="${quote.quote_id}" data-i18n="common.delete">Delete</button>
            </div>
        </div>
    `;
}

function setupEventHandlers() {
    // Search
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
        filterQuotes();
    });

    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    statusFilter.addEventListener('change', () => {
        filterQuotes();
    });

    // Delete modal
    document.getElementById('cancelDeleteBtn').addEventListener('click', hideDeleteModal);
    document.getElementById('confirmDeleteBtn').addEventListener('click', handleDeleteQuote);
}

function filterQuotes() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;

    let filtered = allQuotes;

    // Filter by search term
    if (searchTerm) {
        filtered = filtered.filter(quote => 
            quote.quote_id.toLowerCase().includes(searchTerm) ||
            (quote.notes && quote.notes.toLowerCase().includes(searchTerm))
        );
    }

    // Filter by status
    if (statusFilter !== 'all') {
        filtered = filtered.filter(quote => quote.status === statusFilter);
    }

    displayQuotes(filtered);
}

function showDeleteModal(quoteId) {
    quoteToDelete = quoteId;
    document.getElementById('deleteModal').style.display = 'flex';
}

function hideDeleteModal() {
    quoteToDelete = null;
    document.getElementById('deleteModal').style.display = 'none';
}

async function handleDeleteQuote() {
    if (!quoteToDelete) return;

    try {
        await api.deleteQuote(quoteToDelete);
        
        // Remove from local array
        allQuotes = allQuotes.filter(q => q.quote_id !== quoteToDelete);
        
        // Refresh display
        filterQuotes();
        
        hideDeleteModal();
    } catch (error) {
        console.error('Failed to delete quote:', error);
        alert('Failed to delete quote: ' + error.message);
    }
}
