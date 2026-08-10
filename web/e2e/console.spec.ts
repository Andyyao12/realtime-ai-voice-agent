import { expect, test } from "@playwright/test";

test("preview console is framed and populated", async ({ page }, testInfo) => {
  await page.goto("/?preview=1");

  await expect(page.getByLabel("Harborlight Live")).toBeVisible();
  await expect(page.getByTestId("avatar-stage")).toBeVisible();
  await expect(page.getByTestId("transcript-stream")).toContainText("extra towels");
  await expect(page.getByTestId("status-timeline")).toContainText("Realtime model ready");
  await expect(page.getByTestId("status-timeline")).toContainText("Knowledge found");
  await expect(page.getByTestId("status-timeline")).toContainText("Service request created");
  await expect(page.getByTestId("status-timeline")).not.toContainText("Digital human ready");

  const bodyWidth = await page.locator("body").evaluate((element) => element.scrollWidth);
  const viewportWidth = page.viewportSize()?.width ?? 0;
  expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);

  const outputName = testInfo.project.name === "mobile" ? "console-mobile.png" : "console-desktop.png";
  await page.screenshot({ path: `../docs/media/${outputName}`, fullPage: true });
});
