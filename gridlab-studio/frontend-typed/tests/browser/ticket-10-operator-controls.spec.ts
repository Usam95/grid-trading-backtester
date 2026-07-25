import { expect, test } from "@playwright/test";

test("presents Ticket 10 operator previews and terminal disposal without dispatch authority", async ({ page }) => {
  await page.goto("/studio/");
  await page.getByRole("button", { name: "Operations workspace" }).click();

  await expect(page.getByRole("heading", { name: "Operate controls and terminal disposal" })).toBeVisible();
  await expect(page.getByText("ACTIVATION_PENDING", { exact: true })).toBeVisible();
  await expect(page.getByText(/0\.80000000[\s\S]*reconciliation-ledger/i)).toBeVisible();
  await expect(page.getByText(/cancel 2 obligations · retain 1/i)).toBeVisible();
  await expect(page.getByText(/BLOCKED · current_evidence · reconciliation · command_authority/i)).toBeVisible();
  await expect(page.getByText(/PREVIEW_REQUIRED · DISPOSE · 1 late fills admitted/i)).toBeVisible();
  await expect(page.getByText(/NONE · DISPOSED/i)).toBeVisible();
  await expect(page.getByText(/GAP_THROUGH .* RESIDUAL_HOLDINGS/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /pause|resume|stop|emergency/i })).toHaveCount(0);
});
