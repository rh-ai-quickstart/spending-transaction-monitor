import config from '@spending-monitor/eslint-config';

export default [
  ...config,
  {
    ignores: ['e2e/**'],
  },
];
