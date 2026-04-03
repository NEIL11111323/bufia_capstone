window.BufiaMemberAutocomplete = (function () {
    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function init(config) {
        const nameInput = document.getElementById(config.nameInputId);
        const selectedMemberInput = document.getElementById(config.selectedMemberId);
        const resultsBox = document.getElementById(config.resultsId);
        const contactInput = config.contactInputId ? document.getElementById(config.contactInputId) : null;
        const addressInput = config.addressInputId ? document.getElementById(config.addressInputId) : null;
        const areaInput = config.areaInputId ? document.getElementById(config.areaInputId) : null;
        const badge = config.badgeId ? document.getElementById(config.badgeId) : null;
        const endpoint = config.endpoint;
        let activeResults = [];

        if (!nameInput || !selectedMemberInput || !resultsBox || !endpoint) {
            return;
        }

        function setBadge(mode) {
            if (!badge) return;
            if (mode === 'member') {
                badge.className = 'badge bg-success-subtle text-success border border-success-subtle';
                badge.textContent = 'Member';
                return;
            }
            if (mode === 'walk-in') {
                badge.className = 'badge bg-warning-subtle text-warning border border-warning-subtle';
                badge.textContent = 'Walk-in';
                return;
            }
            badge.className = 'badge bg-secondary-subtle text-secondary border border-secondary-subtle';
            badge.textContent = 'Type to search';
        }

        function clearResults() {
            resultsBox.innerHTML = '';
            resultsBox.style.display = 'none';
            activeResults = [];
        }

        function clearSelectedMember() {
            selectedMemberInput.value = '';
            setBadge(nameInput.value.trim() ? 'walk-in' : 'idle');
            nameInput.dispatchEvent(new CustomEvent('member-autocomplete:change', {
                bubbles: true,
                detail: {
                    mode: nameInput.value.trim() ? 'walk-in' : 'idle',
                    member: null,
                },
            }));
        }

        function applyMember(member) {
            nameInput.value = member.name || '';
            selectedMemberInput.value = member.id || '';
            if (contactInput) contactInput.value = member.contact_number || '';
            if (addressInput) addressInput.value = member.address || '';
            if (areaInput && member.farm_area) areaInput.value = member.farm_area;
            setBadge('member');
            nameInput.dispatchEvent(new CustomEvent('member-autocomplete:change', {
                bubbles: true,
                detail: {
                    mode: 'member',
                    member,
                },
            }));
            clearResults();
        }

        function renderResults(results) {
            activeResults = results;
            if (!results.length) {
                resultsBox.innerHTML = '<div class="list-group-item small text-muted">No member found. Continue typing to book as walk-in.</div>';
                resultsBox.style.display = 'block';
                return;
            }

            resultsBox.innerHTML = results.map((member, index) => `
                <button type="button" class="list-group-item list-group-item-action" data-member-index="${index}">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <div>
                            <div class="fw-semibold">${escapeHtml(member.name)}</div>
                            <div class="small text-muted">${escapeHtml(member.address || 'No address saved')}</div>
                        </div>
                        <span class="badge bg-success-subtle text-success border border-success-subtle">Member</span>
                    </div>
                    ${member.contact_number ? `<div class="small text-muted mt-1">${escapeHtml(member.contact_number)}</div>` : ''}
                </button>
            `).join('');
            resultsBox.style.display = 'block';
        }

        async function searchMembers() {
            const query = nameInput.value.trim();
            if (query.length < 2) {
                clearResults();
                clearSelectedMember();
                return;
            }

            try {
                const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin',
                });
                if (!response.ok) {
                    throw new Error('Search failed');
                }
                const payload = await response.json();
                renderResults(payload.results || []);
                if (!selectedMemberInput.value) {
                    setBadge('walk-in');
                }
            } catch (error) {
                clearResults();
            }
        }

        nameInput.addEventListener('input', function () {
            clearSelectedMember();
            searchMembers();
        });

        resultsBox.addEventListener('click', function (event) {
            const button = event.target.closest('[data-member-index]');
            if (!button) return;
            const member = activeResults[Number(button.dataset.memberIndex)];
            if (member) {
                applyMember(member);
            }
        });

        document.addEventListener('click', function (event) {
            if (event.target === nameInput || resultsBox.contains(event.target)) {
                return;
            }
            clearResults();
        });

        if (selectedMemberInput.value) {
            setBadge('member');
        } else {
            setBadge(nameInput.value.trim() ? 'walk-in' : 'idle');
        }
    }

    return { init };
})();
