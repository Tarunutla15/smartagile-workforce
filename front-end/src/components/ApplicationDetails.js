import React, { useContext } from 'react';
import { useParams } from 'react-router-dom';
import { AppDataContext } from '../Dashboards/EmployeeDBComponent/AppDataProvider';
import './ApplicationDetails.css'; // Import the CSS file

const formatDuration = (durationInMinutes) => {
    const hours = Math.floor(durationInMinutes / 60); // Get the whole number of hours
    const minutes = Math.round(durationInMinutes % 60); // Get the remaining minutes after hours
  
    if (hours > 0 && minutes > 0) {
      return `${hours}hr ${minutes}min`; // If both hours and minutes are present
    } else if (hours > 0) {
      return `${hours}hr`; // If only hours
    } else {
      return `${minutes}min`; // If only minutes
    }
  };

const ApplicationDetails = () => {
  const { filteredData, loading } = useContext(AppDataContext);
  const { appName } = useParams();

  // Filter data for the selected application
  const filteredAppData = filteredData.filter(item =>
    item.applicationname.trim().toLowerCase() === appName.trim().toLowerCase()
  );

  // Sort data by date
  const sortedAppData = filteredAppData.sort((a, b) => {
    const dateA = new Date(a.date);
    const dateB = new Date(b.date);
    return dateB - dateA; // Sort descending by date
  });

  // If still loading, show a loading message
  if (loading) {
    return <div>Loading...</div>;
  }

  // If no data found, show an error message
  if (sortedAppData.length === 0) {
    return <div>No data found for the selected application.</div>;
  }

  return (
    <div className="application-details-container">
      <h1 className="application-details-header">{appName} Details</h1>
      <table className="application-details-table">
        <thead>
          <tr>
            <th>Task</th>
            <th>Category</th>
            <th>Duration (minutes)</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {sortedAppData.map((item, index) => (
            <tr key={index}>
              <td>{item.task}</td>
              <td>{item.category}</td>
              <td>{formatDuration(Math.ceil(item.duration/60))}</td>
              <td>{item.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ApplicationDetails;
