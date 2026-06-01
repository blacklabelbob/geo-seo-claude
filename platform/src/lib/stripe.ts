import Stripe from "stripe";

export const stripe = new Stripe(
  process.env.STRIPE_SECRET_KEY ?? "sk_test_placeholder",
);

export const stripeConfigured = () =>
  !!process.env.STRIPE_SECRET_KEY &&
  !process.env.STRIPE_SECRET_KEY.includes("placeholder");

/** The recurring SaaS plans (amounts in cents). Premium DFY is sales-assisted. */
export const PLANS: Record<
  string,
  { name: string; amount: number; interval: "month" }
> = {
  pro: { name: "Auto-Remediate", amount: 59700, interval: "month" },
  agency: { name: "Agency", amount: 149700, interval: "month" },
};
