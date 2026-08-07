import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function IconBase({ children, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height="20"
      viewBox="0 0 24 24"
      width="20"
      {...props}
    >
      {children}
    </svg>
  );
}

export function DashboardIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6V11h-6v9Zm0-16v5h6V4h-6Z" stroke="currentColor" strokeWidth="1.8" />
    </IconBase>
  );
}

export function OrganisationIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 20V7l8-3 8 3v13M8 10h2m4 0h2m-8 4h2m4 0h2M9 20v-3h6v3" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </IconBase>
  );
}

export function InventoryIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M6 3h9l3 3v15H6V3Zm9 0v4h4M9 11h6m-6 4h6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </IconBase>
  );
}

export function ActivityIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 13h4l2-7 4 12 2-5h4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9" />
    </IconBase>
  );
}

export function ReviewIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 4h14v16H5V4Zm4 4h6m-6 4h6m-6 4h4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </IconBase>
  );
}

export function ApprovalIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="m5 12 4 4L19 6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </IconBase>
  );
}

export function ReportIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 3h14v18H5V3Zm4 12 2-3 2 2 3-5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </IconBase>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </IconBase>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </IconBase>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </IconBase>
  );
}


export function UploadIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path
        d="M12 16V4m0 0L7 9m5-5 5 5M5 14v6h14v-6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </IconBase>
  );
}
