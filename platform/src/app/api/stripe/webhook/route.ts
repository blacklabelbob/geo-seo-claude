import { NextResponse } from "next/server";
import { stripe, stripeConfigured } from "@/lib/stripe";
import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";

export async function POST(request: Request) {
  if (!stripeConfigured() || !process.env.STRIPE_WEBHOOK_SECRET) {
    return NextResponse.json({ received: true, skipped: "not configured" });
  }

  const sig = request.headers.get("stripe-signature");
  const body = await request.text();
  let event;
  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig ?? "",
      process.env.STRIPE_WEBHOOK_SECRET,
    );
  } catch (e) {
    return NextResponse.json(
      { error: `Webhook signature failed: ${e instanceof Error ? e.message : ""}` },
      { status: 400 },
    );
  }

  const admin = createAdminClient();

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const orgId = session.metadata?.org_id;
    const plan = session.metadata?.plan ?? "pro";
    if (orgId) {
      await admin.from("subscriptions").upsert(
        {
          org_id: orgId,
          stripe_customer_id:
            typeof session.customer === "string" ? session.customer : null,
          stripe_subscription_id:
            typeof session.subscription === "string"
              ? session.subscription
              : null,
          plan,
          status: "active",
        },
        { onConflict: "org_id" },
      );
      await admin.from("orgs").update({ plan }).eq("id", orgId);
    }
  }

  if (
    event.type === "customer.subscription.updated" ||
    event.type === "customer.subscription.deleted"
  ) {
    const sub = event.data.object;
    const status = event.type.endsWith("deleted") ? "canceled" : sub.status;
    await admin
      .from("subscriptions")
      .update({ status: status as string })
      .eq("stripe_subscription_id", sub.id);
  }

  return NextResponse.json({ received: true });
}
