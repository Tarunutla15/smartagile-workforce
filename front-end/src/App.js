import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom"; // Correctly import from react-router-dom
import Login from "./components/Login.js";
import AdminLogin from "./components/AdminLogin.js";
import Signup from "./components/Signup.js";
import About from "./components/About.js";
import ForgotPassword from "./components/ForgotPassword";
import UserProfile from "./components/UserProfile";
import EmployeeDashboard from "./Dashboards/EmployeeDBComponent/EmployeeDashboard";
import GroupDashboard from "./Dashboards/GroupDBComponent/GroupDashboard";
import SprintDashboard from "./Dashboards/SprintDBComponents/SprintDashboard";
import LandingPage from "./components/LandingPage.js";
import LoginPage from "./components/LoginPage.js";
import PasswordReset from "./components/PasswordReset.js";
import EmployeeProfiles from "./components/EmployeeProfiles.js";
import ApplicationDetails from "./components/ApplicationDetails.js";
import RequireAdmin from "./components/RequireAdmin.jsx";
import AdminOrgDashboard from "./Dashboards/AdminOrg/AdminOrgDashboard.jsx";
import DataCollectionPage from "./components/DataCollectionPage.jsx";
import AssistantChatWidget from "./components/AssistantChatWidget";

function App() {
  return (
    <>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/adminlogin" element={<AdminLogin />} />
        <Route path="/loging" element={<Login />} />
        <Route path="/about" element={<About />} />
        <Route path="/data-collection" element={<DataCollectionPage />} />
        <Route path="/signup" element={<Signup />} />

        <Route path="/forget/resetpassword" element={<PasswordReset />} />
        <Route path="/forget" element={<ForgotPassword />} />
        <Route path="/employee/dashboard" element={<EmployeeDashboard />} />
        <Route path="/employee-profiles" element={<UserProfile />} />
        <Route path="/group/dashboard" element={<GroupDashboard />} />
        <Route
          path="/admin/dashboard"
          element={
            <RequireAdmin>
              <AdminOrgDashboard />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/sprint-dashboard"
          element={
            <RequireAdmin>
              <SprintDashboard />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/employee-profiles"
          element={
            <RequireAdmin>
              <EmployeeProfiles />
            </RequireAdmin>
          }
        />
        <Route path="/application-details/:appName" element={<ApplicationDetails />} />
        {/* Add other routes as needed */}
      </Routes>
    </BrowserRouter>
    <AssistantChatWidget />
    </>
  );
}

export default App;