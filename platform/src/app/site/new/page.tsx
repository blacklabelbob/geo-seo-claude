import { redirect } from "next/navigation";
import { requireUser, getPrimaryOrg } from "@/lib/auth";
import { NavBar, Panel } from "@/components/ui";
import { domainFromUrl } from "@/lib/util";

async function addSite(formData: FormData) {
  "use server";
  const { supabase } = await requireUser();
  const org = await getPrimaryOrg(supabase);
  if (!org) redirect("/");

  const raw = String(formData.get("url") ?? "").trim();
  if (!raw) redirect("/site/new");
  const url = raw.startsWith("http") ? raw : `https://${raw}`;
  const name = String(formData.get("name") ?? "").trim();
  const domain = domainFromUrl(url);

  const { data } = await supabase
    .from("sites")
    .insert({
      org_id: org.id,
      url,
      domain,
      name: name || domain,
      status: "new",
    })
    .select()
    .single();

  redirect(data ? `/site/${data.id}` : "/");
}

export default async function NewSite() {
  const { supabase } = await requireUser();
  const org = await getPrimaryOrg(supabase);
  return (
    <>
      <NavBar orgName={org?.name} />
      <main className="mx-auto max-w-xl px-6 py-10">
        <h1 className="mb-1 text-2xl font-extrabold">Add a website</h1>
        <p className="mb-6 text-sm text-dim">
          Add a site, then run a GEO audit to score its AI-search visibility.
        </p>
        <Panel>
          <form action={addSite} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wider text-dim">
                Website URL
              </label>
              <input
                name="url"
                required
                placeholder="example.com"
                className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wider text-dim">
                Name (optional)
              </label>
              <input
                name="name"
                placeholder="Acme Roofing"
                className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
              />
            </div>
            <button className="rounded-md bg-blue px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
              Add website
            </button>
          </form>
        </Panel>
      </main>
    </>
  );
}
