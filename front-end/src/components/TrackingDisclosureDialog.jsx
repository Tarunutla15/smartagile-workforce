import React, { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
} from "@mui/material";
import DataCollectionMui from "./DataCollectionMui";
import { DISCLOSURE_VERSION } from "../content/dataCollectionCopy";

export const DATA_DISCLOSURE_STORAGE_KEY = `sa_data_disclosure_ack_${DISCLOSURE_VERSION}`;

/**
 * First-visit modal so users read disclosure before using dashboards (web cannot stop the desktop agent).
 */
export default function TrackingDisclosureDialog() {
  const [open, setOpen] = useState(false);
  const [read, setRead] = useState(false);

  useEffect(() => {
    try {
      if (!window.localStorage.getItem(DATA_DISCLOSURE_STORAGE_KEY)) {
        setOpen(true);
      }
    } catch {
      setOpen(true);
    }
  }, []);

  const acknowledge = () => {
    try {
      window.localStorage.setItem(DATA_DISCLOSURE_STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
    setOpen(false);
  };

  return (
    <Dialog
      open={open}
      onClose={() => {}}
      disableEscapeKeyDown
      fullWidth
      maxWidth="md"
      aria-labelledby="tracking-disclosure-title"
    >
      <DialogTitle id="tracking-disclosure-title">Before you use activity data</DialogTitle>
      <DialogContent dividers sx={{ maxHeight: "70vh" }}>
        <DataCollectionMui showAdminAudience />
      </DialogContent>
      <DialogActions
        sx={{
          flexDirection: "column",
          alignItems: "stretch",
          px: 3,
          pb: 2,
          pt: 1,
          gap: 1,
        }}
      >
        <FormControlLabel
          control={<Checkbox checked={read} onChange={(e) => setRead(e.target.checked)} color="primary" />}
          label="I have read the above. I understand what the desktop agent can collect when it runs."
        />
        <Button variant="contained" disabled={!read} onClick={acknowledge} sx={{ bgcolor: "#4f46e5" }}>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
