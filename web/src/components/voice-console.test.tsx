/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VoiceConsole } from "./voice-console";

describe("VoiceConsole", () => {
  it("renders the operational console as the first screen", () => {
    render(<VoiceConsole />);

    expect(screen.getByLabelText("Harborlight Live")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start call" })).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Live transcript" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Capability status" })).toBeInTheDocument();
  });
});
