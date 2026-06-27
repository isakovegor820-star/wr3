import type { SVGProps } from 'react';

export function SendIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      {...props}
    >
      <path d="M21.94 4.6L3.3 11.78c-.93.36-.92 1.7.01 2.05l4.6 1.7 1.77 5.6c.28.9 1.43 1.08 1.97.3l2.5-3.62 4.7 3.47c.6.44 1.45.12 1.62-.6L23.9 5.6c.2-.85-.64-1.53-1.42-1.18zM9.5 14.7l9.4-5.92-7.8 7.1c-.2.18-.33.43-.37.7l-.28 2.06-.95-3.04c-.06-.2.0-.4.0-.5z" />
    </svg>
  );
}
