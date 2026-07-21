import { expect, test } from "@playwright/test";

test("operator completes and reloads the migrated typed backtest while legacy stays available", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/studio/");
  await expect(page.getByText("NO ONLINE TRADING AUTHORITY")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Studio" })).toContainText(
    "Command Center",
  );

  await page.getByLabel("Symbol").fill("ETHUSDT");
  await page.getByLabel("Synthetic bars").fill("300");
  await page.getByRole("combobox", { name: "Spacing" }).selectOption("geometric");
  await page.getByRole("button", { name: "Run backtest" }).click();

  await expect(
    page.getByRole("heading", { name: "ETHUSDT primary result" }),
  ).toBeVisible();
  await expect(page.getByText("Authoritative local record")).toBeVisible();
  const runId = await page.locator(".record code").innerText();
  await expect(page).toHaveURL(new RegExp(`/experiments/${runId}$`));

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "ETHUSDT primary result" }),
  ).toBeVisible();
  await expect(page.locator(".record code")).toHaveText(runId);

  await page.getByRole("button", { name: "Operations workspace" }).click();
  await expect(page.getByText("No commands are cached or queued by this browser.")).toBeVisible();
  await expect(page.getByRole("button", { name: /pause|stop|activate/i })).toHaveCount(0);

  await page.goto("/");
  await expect(page.getByText("gridlab studio", { exact: true })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});
