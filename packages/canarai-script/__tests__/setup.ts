import { afterEach } from 'vitest';

afterEach(() => {
  // Reset DOM between tests
  document.head.innerHTML = '';
  document.body.innerHTML = '';

  // Clear any window globals we set
  delete (window as any).__CANARAI_CONFIG__;
});
