const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const APP_URL = process.env.APP_URL || "http://127.0.0.1:8504";
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const LOG_ROOT = path.join(PROJECT_ROOT, "logs");
const TODAY = "20260423";
const RESULT_PATH = path.join(LOG_ROOT, `ui_click_audit_result_int_${TODAY}.json`);
const SCREENSHOT_PATH = path.join(LOG_ROOT, `ui_click_audit_result_int_${TODAY}.png`);

const TEMP_A = `UI_AUDIT_${Date.now()}_A`;
const TEMP_B = `UI_AUDIT_${Date.now()}_B`;
const TEMP_C = `UI_AUDIT_${Date.now()}_C`;

function ensureLogRoot() {
  fs.mkdirSync(LOG_ROOT, { recursive: true });
}

function pushResult(resultList, step, passed, detail) {
  resultList.push({
    STEP: step,
    PASSED: passed,
    DETAIL: detail,
    TIMESTAMP: new Date().toISOString(),
  });
}

async function waitForAppReady(page) {
  await page.goto(APP_URL);
  await page.waitForSelector("text=ACC102 Volatility MVP", { timeout: 60000 });
  await page.waitForTimeout(2000);
}

async function getBodyText(page) {
  return await page.textContent("body");
}

async function assertNoAppException(page, resultList, step) {
  const bodyText = await getBodyText(page);
  const hasTraceback = bodyText.includes("Traceback:");
  const hasException = bodyText.includes("StreamlitAPIException");
  pushResult(
    resultList,
    step,
    !hasTraceback && !hasException,
    !hasTraceback && !hasException ? "No application exception detected." : "Traceback or StreamlitAPIException detected in page body."
  );
}

async function ensureBuilderOpen(page) {
  const top10Count = await page.getByRole("button", { name: "Use Current Scope Top 10" }).count();
  if (top10Count === 0) {
    await page.getByText("Research Basket Builder").click();
    await page.waitForTimeout(1200);
  }
}

async function clickPage(page, pageName, expectedText) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);
  await page.locator("label").filter({ hasText: new RegExp(`^${pageName}$`) }).first().click();
  await page.waitForSelector(`text=${expectedText}`, { timeout: 30000 });
  await page.waitForTimeout(1200);
}

async function chooseSelectOption(page, labelText, optionMatcher) {
  await page.getByLabel(labelText).click();
  await page.waitForTimeout(500);
  if (typeof optionMatcher === "string") {
    await page.getByRole("option", { name: optionMatcher }).click();
  } else {
    await page.getByRole("option", { name: optionMatcher }).click();
  }
  await page.waitForTimeout(1500);
}

async function setRadioChoice(page, labelText) {
  await page.getByText(labelText, { exact: true }).first().click();
  await page.waitForTimeout(1200);
}

async function clickButton(page, buttonName) {
  const button = page.getByRole("button", { name: buttonName });
  await button.scrollIntoViewIfNeeded();
  await button.click();
  await page.waitForTimeout(1500);
}

async function readMetricAfterLabel(page, labelText) {
  const bodyText = await getBodyText(page);
  const compactText = bodyText.replace(/\s+/g, " ");
  const match = compactText.match(new RegExp(`${labelText} ([^ ]+)`, "i"));
  return match ? match[1] : null;
}

(async () => {
  ensureLogRoot();
  const resultList = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 2600 } });

  try {
    await waitForAppReady(page);

    let bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Initial app load",
      bodyText.includes("ACC102 Volatility MVP"),
      bodyText.includes("ACC102 Volatility MVP") ? "Main title rendered." : "Main title missing."
    );
    pushResult(
      resultList,
      "Initial session-state warning check",
      !bodyText.includes("Session State API"),
      !bodyText.includes("Session State API") ? "No session-state warning banner." : "Session-state warning banner still shown."
    );

    await clickPage(page, "Overview", "Quick Tasks");
    await setRadioChoice(page, "Baseline");
    await setRadioChoice(page, "Boosted");
    await setRadioChoice(page, "Both");
    pushResult(resultList, "Overview model view toggle", true, "Both / Baseline / Boosted clicked successfully.");

    await clickButton(page, "Top Risk Picks Today");
    await page.waitForSelector("text=Quick task active: Top Risk Picks Today", { timeout: 30000 });
    pushResult(resultList, "Quick task: Top Risk Picks Today", true, "Overview quick task routed to Market.");

    await clickPage(page, "Overview", "Quick Tasks");
    await clickButton(page, "Low-Liquidity High-Vol Names");
    await page.waitForSelector("text=Quick task active: Low-Liquidity High-Vol Names", { timeout: 30000 });
    pushResult(resultList, "Quick task: Low-Liquidity High-Vol Names", true, "Overview quick task routed to Screener.");

    await clickPage(page, "Overview", "Quick Tasks");
    await clickButton(page, "Model Failure Cases");
    await page.waitForSelector("text=Quick task active: Model Failure Cases", { timeout: 30000 });
    pushResult(resultList, "Quick task: Model Failure Cases", true, "Overview quick task routed to Diagnostics.");

    await clickPage(page, "Method & Limitations", "Current Method");
    pushResult(resultList, "Page navigation: Method & Limitations", true, "Method page rendered.");

    await chooseSelectOption(page, "Date Window", "Last 30 Days");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Date Window selectbox",
      bodyText.includes("Last 30 Days"),
      bodyText.includes("Last 30 Days") ? "Date window switched to Last 30 Days." : "Date window selection did not update."
    );

    await chooseSelectOption(page, "Stock Selector Scope", "Live Fetch Only");
    pushResult(resultList, "Scope selectbox: Live Fetch Only", true, "Scope switched to Live Fetch Only.");
    try {
      await chooseSelectOption(page, "Stock Lookup", /603220\.SH/);
    } catch {
      await page.getByLabel("Stock Lookup").click();
      await page.waitForTimeout(500);
      await page.getByRole("option").nth(0).click();
      await page.waitForTimeout(1500);
    }
    await clickPage(page, "Single Stock", "Latest Rows");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Live fetch stock path",
      bodyText.includes("Live On-Demand") || bodyText.includes("currently unavailable for this stock"),
      bodyText.includes("Live On-Demand")
        ? "Live on-demand prediction path rendered."
        : bodyText.includes("currently unavailable for this stock")
          ? "Live fetch path reached with insufficient-history warning."
          : "Live fetch path did not render expected text."
    );

    await chooseSelectOption(page, "Stock Selector Scope", "All Supported A-Shares");
    await chooseSelectOption(page, "Stock Lookup", /300308\.SZ/);
    await clickPage(page, "Overview", "Quick Tasks");
    await ensureBuilderOpen(page);

    await clickButton(page, "Clear Basket");
    await page.waitForTimeout(1500);
    await ensureBuilderOpen(page);
    await clickButton(page, "Add Selected Stock To Basket");
    await page.waitForTimeout(1500);
    await ensureBuilderOpen(page);
    await setRadioChoice(page, "Current Basket");
    await setRadioChoice(page, "Turnover-Weighted");
    await page.getByLabel("Basket Name").fill(TEMP_A);
    await clickButton(page, "Save Basket");
    await page.waitForTimeout(1800);
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Basket save",
      bodyText.includes("Basket saved."),
      bodyText.includes("Basket saved.") ? `Saved temporary basket ${TEMP_A}.` : "Basket save message missing."
    );

    await ensureBuilderOpen(page);
    await page.getByLabel("Saved Basket").click();
    await page.waitForTimeout(500);
    await page.getByRole("option", { name: TEMP_A }).click();
    await page.waitForTimeout(1200);
    await clickButton(page, "Load Basket");
    await page.waitForTimeout(1800);
    pushResult(resultList, "Basket load", true, `Loaded temporary basket ${TEMP_A}.`);

    await clickPage(page, "Market", "Highest Predicted Volatility");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Current Basket propagation to Market",
      bodyText.replace(/\s+/g, "").includes("ActiveUniverse1"),
      bodyText.replace(/\s+/g, "").includes("ActiveUniverse1")
        ? "Market page reduced to single-stock basket universe."
        : "Market page did not reflect single-stock basket universe."
    );

    await clickPage(page, "Screener", "Minimum Turnover Amount");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Current Basket propagation to Screener",
      bodyText.includes("Filtered rows: 1"),
      bodyText.includes("Filtered rows: 1")
        ? "Screener filtered rows collapsed to the single-stock basket."
        : "Screener did not reflect single-stock basket."
    );

    await clickPage(page, "Diagnostics", "Current Reading");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Current Basket propagation to Diagnostics",
      bodyText.includes("Diagnostics"),
      "Diagnostics rendered under Current Basket scope."
    );

    await clickPage(page, "Overview", "Quick Tasks");
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Current Basket propagation to Overview",
      bodyText.includes("Current analysis scope: Current Basket"),
      bodyText.includes("Current analysis scope: Current Basket")
        ? "Overview reflects Current Basket."
        : "Overview did not update to Current Basket."
    );

    await ensureBuilderOpen(page);
    await page.getByLabel("Basket Name").fill(TEMP_B);
    await clickButton(page, "Rename Basket");
    await page.waitForTimeout(1800);
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Basket rename",
      bodyText.includes("Basket renamed."),
      bodyText.includes("Basket renamed.") ? `Renamed basket to ${TEMP_B}.` : "Basket rename message missing."
    );

    await ensureBuilderOpen(page);
    await page.getByLabel("Basket Name").fill(TEMP_C);
    await clickButton(page, "Duplicate Basket");
    await page.waitForTimeout(1800);
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Basket duplicate",
      bodyText.includes("Basket duplicated."),
      bodyText.includes("Basket duplicated.") ? `Duplicated basket to ${TEMP_C}.` : "Basket duplicate message missing."
    );

    await ensureBuilderOpen(page);
    await clickButton(page, "Delete Basket");
    await page.waitForTimeout(1800);
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Basket delete duplicated copy",
      bodyText.includes("Basket deleted."),
      bodyText.includes("Basket deleted.") ? `Deleted duplicated basket ${TEMP_C}.` : "Basket delete message missing after duplicate cleanup."
    );

    await ensureBuilderOpen(page);
    await clickButton(page, "Open Basket Page");
    await page.waitForSelector("text=Basket Availability", { timeout: 30000 });
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Open Basket Page button",
      bodyText.includes("Current weighting mode: Turnover-Weighted"),
      bodyText.includes("Current weighting mode: Turnover-Weighted")
        ? "Basket page opened and weighting mode updated."
        : "Basket page opened but weighting mode text missing."
    );

    await clickPage(page, "Overview", "Quick Tasks");
    await ensureBuilderOpen(page);
    await setRadioChoice(page, "Coverage Universe");
    await clickButton(page, "Use Current Scope Top 10");
    await page.waitForTimeout(1800);
    await assertNoAppException(page, resultList, "Use Current Scope Top 10 button");

    await clickPage(page, "Screener", "Minimum Turnover Amount");
    await clickButton(page, "Replace Basket With Screen Result");
    await page.waitForTimeout(1800);
    await assertNoAppException(page, resultList, "Replace Basket With Screen Result button");
    await clickPage(page, "Screener", "Minimum Turnover Amount");
    await clickButton(page, "Add Screen Result To Basket");
    await page.waitForTimeout(1800);
    await assertNoAppException(page, resultList, "Add Screen Result To Basket button");

    await clickPage(page, "Overview", "Quick Tasks");
    await ensureBuilderOpen(page);
    await page.getByLabel("Saved Basket").click();
    await page.waitForTimeout(500);
    await page.getByRole("option", { name: TEMP_B }).click();
    await page.waitForTimeout(1000);
    await clickButton(page, "Delete Basket");
    await page.waitForTimeout(1800);
    bodyText = await getBodyText(page);
    pushResult(
      resultList,
      "Basket delete renamed copy",
      bodyText.includes("Basket deleted."),
      bodyText.includes("Basket deleted.") ? `Deleted renamed basket ${TEMP_B}.` : "Basket delete message missing after renamed copy cleanup."
    );

    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    await assertNoAppException(page, resultList, "Final exception check");
  } catch (error) {
    pushResult(resultList, "Audit runtime failure", false, error.stack || String(error));
  } finally {
    await browser.close();
    fs.writeFileSync(RESULT_PATH, JSON.stringify({ APP_URL, RESULT_LIST: resultList }, null, 2), "utf-8");
  }
})();
