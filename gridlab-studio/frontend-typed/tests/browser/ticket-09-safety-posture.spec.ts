import { expect, test } from "@playwright/test";

test("presents Ticket 09 safety facts without command controls", async ({ page }) => {
  await page.goto("/studio/");
  await page.getByRole("button", { name: "Operations workspace" }).click();

  await expect(page.getByRole("heading", { name: "Safety and venue evidence" })).toBeVisible();
  await expect(page.getByText("REDUCE_ONLY", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("RANGE_EXHAUSTED", { exact: true })).toBeVisible();
  await expect(page.getByText("TREND_DOWN", { exact: true })).toBeVisible();
  await expect(page.getByText("DELISTING", { exact: false })).toBeVisible();
  await expect(page.getByText("2025-01-09T12:00:00.000Z", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /pause|resume|stop|emergency|place|cancel/i })).toHaveCount(0);
});
