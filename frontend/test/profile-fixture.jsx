import React from "react";
import { createRoot } from "react-dom/client";
import { ProfilePage } from "../src/pages/ProfilePage";
import { weddingView } from "../src/utils";
import "../src/styles.css";

const wedding = weddingView({
  id: 1, client_id: 2, wedding_date: "2026-06-01", status: 1,
  bridal_trial_status: "not_interested", party_members: [
    { id: 11, role: "B", hairstyle: "U", assistant: false },
    { id: 12, role: "P", hairstyle: "D", assistant: true },
  ],
  client: { id: 2, name: "Test Bride" },
});
createRoot(document.getElementById("root")).render(
  <ProfilePage wedding={wedding} onClose={() => {}} onSaved={() => {}} />,
);
