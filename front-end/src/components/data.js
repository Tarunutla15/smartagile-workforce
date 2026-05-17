import React, { useState, useEffect } from "react";
import { api } from "../api/client";

function DataCheck() {
  const [dataExists, setDataExists] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessError, setAccessError] = useState(null);

  useEffect(() => {
    api
      .get("/api/check_data/")
      .then((response) => {
        setAccessError(null);
        setDataExists(response.data.data_exists);
        setData(response.data.data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching data:", error);
        if (error.response?.status === 401) {
          setDataExists(false);
          setData(null);
          setAccessError("signin");
        } else if (error.response?.status === 403) {
          setDataExists(false);
          setData(null);
          setAccessError("admin");
        } else {
          setAccessError("unknown");
        }
        setLoading(false);
      });
  }, []);

  return (
    <div>
      {loading ? (
        <p>Loading...</p>
      ) : accessError === "signin" ? (
        <p>Sign in required. This page lists users for admins only.</p>
      ) : accessError === "admin" ? (
        <p>Admin access required to view the user list.</p>
      ) : accessError === "unknown" ? (
        <p>Could not load data.</p>
      ) : (
        <div>
          <p>Data exists: {dataExists ? "Yes" : "No"}</p>
          {dataExists && data && Array.isArray(data) && (
            <div>
              <h2>Users:</h2>
              <ul>
                {data.map((item) => (
                  <li key={item.id}>
                    {item.username} — {item.email} ({item.role})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DataCheck;
