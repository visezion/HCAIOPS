// Light rebrand + quick links for Swagger UI
(function () {
  const ready = () => {
    document.body.classList.add('hcai-swagger');

    const brand = document.querySelector('.topbar-wrapper .link span');
    if (brand) brand.textContent = 'HCAI OPS API Docs';

    // Add quick links to the dashboard/model trainer inside Swagger topbar
    const topbar = document.querySelector('.topbar .wrapper');
    if (topbar && !document.querySelector('.hcai-docs-links')) {
      const container = document.createElement('div');
      container.className = 'hcai-docs-links';
      container.style.display = 'flex';
      container.style.alignItems = 'center';
      container.style.gap = '10px';
      container.style.marginLeft = '12px';

      const dashboardLink = document.createElement('a');
      dashboardLink.href = '/web/dashboard.html';
      dashboardLink.textContent = 'Dashboard';
      dashboardLink.style.padding = '8px 12px';
      dashboardLink.style.borderRadius = '10px';
      dashboardLink.style.background = '#0ea5e9';
      dashboardLink.style.color = '#0f172a';
      dashboardLink.style.fontWeight = '600';

      const trainerLink = document.createElement('a');
      trainerLink.href = '/web/train.html';
      trainerLink.textContent = 'Model Trainer';
      trainerLink.style.padding = '8px 12px';
      trainerLink.style.borderRadius = '10px';
      trainerLink.style.background = '#22c55e';
      trainerLink.style.color = '#0f172a';
      trainerLink.style.fontWeight = '600';

      container.appendChild(dashboardLink);
      container.appendChild(trainerLink);
      topbar.appendChild(container);
    }

    // Add a fixed banner under the topbar for consistent navigation
    if (!document.querySelector('.hcai-docs-bar')) {
      const bar = document.createElement('div');
      bar.className = 'hcai-docs-bar';
      const left = document.createElement('div');
      left.textContent = 'HCAI OPS • API Docs';
      left.style.fontWeight = '700';
      left.style.color = '#0f172a';

      const actions = document.createElement('div');
      actions.className = 'hcai-docs-actions';

      const dash = document.createElement('a');
      dash.href = '/web/dashboard.html';
      dash.className = 'hcai-pill';
      dash.textContent = 'Dashboard';

      const trainer = document.createElement('a');
      trainer.href = '/web/train.html';
      trainer.className = 'hcai-pill secondary';
      trainer.textContent = 'Model Trainer';

      actions.appendChild(dash);
      actions.appendChild(trainer);
      bar.appendChild(left);
      bar.appendChild(actions);

      const root = document.querySelector('.swagger-ui')?.parentElement || document.body;
      root.insertBefore(bar, document.querySelector('.swagger-ui'));
    }
  };

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    ready();
  } else {
    document.addEventListener('DOMContentLoaded', ready);
  }
})();
