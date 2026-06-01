import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { stripe, stripeConfigured, PLANS } from "@/lib/stripe";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!stripeConfigured()) {
    return NextResponse.json(
      { error: "Stripe is not configured (set STRIPE_SECRET_KEY)." },
      { status: 503 },
    );
  }

  const { plan } = await request.json().catch(() => ({}));
  const p = PLANS[plan as string];
  if (!p) return NextResponse.json({ error: "Unknown plan" }, { status: 400 });

  const { data: org } = await supabase
    .from("orgs")
    .select("*")
    .limit(1)
    .maybeSingle();
  if (!org) return NextResponse.json({ error: "No org" }, { status: 400 });

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer_email: user.email ?? undefined,
    line_items: [
      {
        price_data: {
          currency: "usd",
          product_data: { name: `GEO Platform — ${p.name}` },
          recurring: { interval: p.interval },
          unit_amount: p.amount,
        },
        quantity: 1,
      },
    ],
    metadata: { org_id: org.id, plan },
    success_url: `${appUrl}/?checkout=success`,
    cancel_url: `${appUrl}/pricing?checkout=cancelled`,
  });

  return NextResponse.json({ url: session.url });
}
