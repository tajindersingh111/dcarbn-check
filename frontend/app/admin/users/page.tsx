"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";

interface Membership {
  id: string;
  email: string;
  full_name: string;
  user_status: string;
  is_active: boolean;
  roles: string[];
  joined_at: string | null;
  last_login_at: string | null;
  failed_login_count: number;
  locked_until: string | null;
}

interface Role {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_system: boolean;
  is_active: boolean;
}

export default function UsersPage() {
  const users = useApiQuery<{ items: Membership[]; total: number }>("/users?limit=200");
  const roles = useApiQuery<Role[]>("/roles");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [invitationToken, setInvitationToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const selected = useMemo(
    () => users.data?.items.find((item) => item.id === selectedId) ?? null,
    [selectedId, users.data]
  );

  function chooseUser(user: Membership) {
    setSelectedId(user.id);
    setSelectedRoles(user.roles);
  }

  async function invite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiRequest<{ invitation_token: string }>("/users/invitations", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          full_name: form.get("full_name"),
          role_names: form.getAll("role_names")
        })
      });
      setInvitationToken(response.invitation_token || "sent");
      await users.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invitation failed.");
    } finally {
      setWorking(false);
    }
  }

  async function saveRoles() {
    if (!selected) return;
    setWorking(true);
    setError(null);
    try {
      await apiRequest(`/users/${selected.id}/roles`, {
        method: "PATCH",
        body: JSON.stringify({ role_names: selectedRoles })
      });
      await users.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Role update failed.");
    } finally {
      setWorking(false);
    }
  }

  async function unlockAccount() {
    if (!selected) return;
    setWorking(true);
    setError(null);
    try {
      await apiRequest(`/users/${selected.id}/unlock`, { method: "POST" });
      await users.refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Account unlock failed."
      );
    } finally {
      setWorking(false);
    }
  }

  async function toggleStatus() {
    if (!selected) return;
    setWorking(true);
    setError(null);
    try {
      await apiRequest(`/users/${selected.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !selected.is_active })
      });
      await users.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Status update failed.");
    } finally {
      setWorking(false);
    }
  }

  if (users.loading || roles.loading) return <LoadingState label="Loading users" />;
  if (users.error || roles.error) return <ErrorState message={users.error ?? roles.error ?? "Unknown error"} onRetry={() => { void users.refresh(); void roles.refresh(); }} />;

  return (
    <>
      <PageHeader eyebrow="Access administration" title="Users and roles" description="Invite users, assign least-privilege roles, and revoke tenant access." actions={<button className="button button-primary" onClick={() => { setInvitationToken(null); setInviteOpen(true); }} type="button">Invite user</button>} />
      <section className="split-layout">
        <article className="panel">
          <DataTable caption="Tenant users" headers={["User", "Roles", "Last login", "Status"]}>
            {(users.data?.items ?? []).map((user) => <tr className={user.id === selectedId ? "selected-row" : ""} key={user.id} onClick={() => chooseUser(user)}><td><div className="stacked-cell"><strong>{user.full_name}</strong><span>{user.email}</span></div></td><td>{user.roles.join(", ")}</td><td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString("en-GB") : "Never"}</td><td><StatusBadge status={user.is_active ? user.user_status : "disabled"} /></td></tr>)}
          </DataTable>
        </article>
        <aside className="panel detail-panel">
          {selected ? <>
            <div className="panel-heading"><div><p className="eyebrow">Access profile</p><h2>{selected.full_name}</h2></div></div>
            <div className="role-checkboxes">
              {(roles.data ?? []).map((role) => <label className="checkbox-field" key={role.id}><input checked={selectedRoles.includes(role.name)} onChange={(event) => setSelectedRoles((current) => event.target.checked ? [...current, role.name] : current.filter((name) => name !== role.name))} type="checkbox" /> <span><strong>{role.display_name}</strong><small>{role.description}</small></span></label>)}
            </div>
            <MutationMessage error={error} />
            <div className="button-row">{selected.locked_until ? <button className="button button-secondary" disabled={working} onClick={() => void unlockAccount()} type="button">Unlock account</button> : null}<button className="button button-secondary" disabled={working} onClick={() => void toggleStatus()} type="button">{selected.is_active ? "Deactivate access" : "Reactivate access"}</button><button className="button button-primary" disabled={working || selectedRoles.length === 0} onClick={() => void saveRoles()} type="button">Save roles</button></div>
          </> : <p>Select a user to administer access.</p>}
        </aside>
      </section>

      <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Invite user" description="Issue a time-limited invitation for this tenant.">
        {invitationToken ? (
          <div className="token-panel">
            <strong>Invitation created</strong>
            {invitationToken !== "sent" ? (
              <>
                <p>Share this link through your approved secure channel:</p>
                <code>{`${window.location.origin}/accept-invitation?token=${invitationToken}`}</code>
              </>
            ) : (
              <p>Invitation emailed to the user.</p>
            )}
          </div>
        ) : (
          <form className="modal-form" onSubmit={invite}>
            <label>Full name<input name="full_name" required /></label>
            <label>Email address<input name="email" required type="email" /></label>
            <fieldset>
              <legend>Roles</legend>
              {(roles.data ?? []).map((role) => (
                <label className="checkbox-field" key={role.id}>
                  <input name="role_names" type="checkbox" value={role.name} /> {role.display_name}
                </label>
              ))}
            </fieldset>
            <MutationMessage error={error} />
            <div className="button-row modal-actions">
              <button className="button button-secondary" onClick={() => setInviteOpen(false)} type="button">Cancel</button>
              <button className="button button-primary" disabled={working} type="submit">
                {working ? "Inviting…" : "Create invitation"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
