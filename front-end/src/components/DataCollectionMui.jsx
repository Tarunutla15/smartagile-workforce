import React from "react";
import {
  Alert,
  Box,
  Divider,
  List,
  ListItem,
  ListItemText,
  Typography,
} from "@mui/material";
import {
  COLLECTED_ITEMS,
  NOT_COLLECTED_ITEMS,
  RETENTION_PARAGRAPH,
  TRACKING_SOURCE_PARAGRAPH,
  WHO_CAN_SEE_ADMIN,
  WHO_CAN_SEE_EMPLOYEE,
} from "../content/dataCollectionCopy";

/**
 * Shared disclosure body for employee settings, admin, and first-run dialog.
 */
export default function DataCollectionMui({ showAdminAudience = true }) {
  return (
    <Box sx={{ color: "text.primary" }}>
      <Alert severity="info" sx={{ mb: 2 }}>
        {TRACKING_SOURCE_PARAGRAPH}
      </Alert>

      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
        What we collect
      </Typography>
      <List dense disablePadding sx={{ mb: 2 }}>
        {COLLECTED_ITEMS.map((row) => (
          <ListItem key={row.title} alignItems="flex-start" sx={{ py: 0.75, px: 0 }}>
            <ListItemText
              primary={row.title}
              secondary={row.body}
              primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
              secondaryTypographyProps={{ variant: "body2", color: "text.secondary" }}
            />
          </ListItem>
        ))}
      </List>

      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
        What we do not collect
      </Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5, mb: 2 }}>
        {NOT_COLLECTED_ITEMS.map((line) => (
          <Typography key={line} component="li" variant="body2" sx={{ mb: 0.5 }}>
            {line}
          </Typography>
        ))}
      </Box>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
        Who can see it
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        {WHO_CAN_SEE_EMPLOYEE}
      </Typography>
      {showAdminAudience && (
        <Typography variant="body2" color="text.secondary" paragraph>
          {WHO_CAN_SEE_ADMIN}
        </Typography>
      )}

      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
        Retention
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {RETENTION_PARAGRAPH}
      </Typography>
    </Box>
  );
}
