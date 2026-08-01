import { ActivityForm } from "@/components/activity-form";
import { PageHeader } from "@/components/page-header";

export const metadata = { title: "Activity entry" };

export default function NewActivityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Activity data"
        title="Add emissions activity"
        description="Record source activity data, evidence and governed factor-resolution criteria."
      />
      <ActivityForm />
    </>
  );
}
