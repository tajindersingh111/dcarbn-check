import type { ReactNode } from "react";

export function DataTable({
  headers,
  children,
  caption
}: {
  headers: string[];
  children: ReactNode;
  caption: string;
}) {
  return (
    <div className="table-shell">
      <table>
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
