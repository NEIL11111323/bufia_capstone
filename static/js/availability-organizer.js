window.BufiaAvailabilityOrganizer = (function () {
    let modal;
    let titleEl;
    let subtitleEl;
    let summaryEl;
    let sectionsEl;

    function ensureModal() {
        if (modal) {
            return;
        }

        modal = document.createElement('div');
        modal.className = 'availability-organizer-modal';
        modal.innerHTML = `
            <div class="availability-organizer-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="availabilityOrganizerTitle">
                <div class="availability-organizer-modal__header">
                    <div>
                        <span class="availability-organizer-modal__eyebrow">Availability Organizer</span>
                        <h2 id="availabilityOrganizerTitle" class="availability-organizer-modal__title">Availability Organizer</h2>
                        <p class="availability-organizer-modal__subtitle"></p>
                    </div>
                    <button type="button" class="availability-organizer-modal__close" aria-label="Close availability organizer">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="availability-organizer-modal__body">
                    <div class="availability-organizer-modal__summary">
                        <span class="availability-organizer-modal__summary-title"></span>
                        <p class="availability-organizer-modal__summary-text"></p>
                    </div>
                    <div class="availability-organizer-modal__sections"></div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        titleEl = modal.querySelector('.availability-organizer-modal__title');
        subtitleEl = modal.querySelector('.availability-organizer-modal__subtitle');
        summaryEl = modal.querySelector('.availability-organizer-modal__summary');
        sectionsEl = modal.querySelector('.availability-organizer-modal__sections');

        modal.addEventListener('click', function (event) {
            if (event.target === modal || event.target.closest('.availability-organizer-modal__close')) {
                hide();
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && modal.classList.contains('is-open')) {
                hide();
            }
        });
    }

    function sectionTemplate(section) {
        return `
            <section class="availability-organizer-modal__section">
                <h3 class="availability-organizer-modal__section-title">${section.title || ''}</h3>
                ${section.html || '<div class="availability-organizer-modal__empty">No availability details available right now.</div>'}
            </section>
        `;
    }

    function show(config) {
        ensureModal();
        titleEl.textContent = config.title || 'Availability Organizer';
        subtitleEl.textContent = config.subtitle || '';

        const summaryTone = config.summaryTone || 'warning';
        summaryEl.className = `availability-organizer-modal__summary is-${summaryTone}`;
        summaryEl.querySelector('.availability-organizer-modal__summary-title').textContent = config.summaryTitle || 'Check your schedule';
        summaryEl.querySelector('.availability-organizer-modal__summary-text').textContent = config.summaryText || 'Review the available dates and time windows below.';

        const sections = Array.isArray(config.sections) ? config.sections : [];
        sectionsEl.innerHTML = sections.map(sectionTemplate).join('');

        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden';
    }

    function hide() {
        if (!modal) {
            return;
        }
        modal.classList.remove('is-open');
        document.body.style.overflow = 'auto';
    }

    function itemList(items) {
        if (!items || !items.length) {
            return '<div class="availability-organizer-modal__empty">No availability suggestions available right now.</div>';
        }

        return `
            <div class="availability-organizer-modal__list">
                ${items.map((item) => `
                    <div class="availability-organizer-modal__item">
                        <div class="availability-organizer-modal__item-main">
                            <span class="availability-organizer-modal__item-title">${item.title || ''}</span>
                            ${item.text ? `<span class="availability-organizer-modal__item-text">${item.text}</span>` : ''}
                        </div>
                        ${item.badge ? `<span class="availability-organizer-modal__badge is-${item.tone || 'success'}">${item.badge}</span>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }

    return {
        show,
        hide,
        itemList,
    };
})();
