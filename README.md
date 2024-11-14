# ⚡ Charge@Large Platform Initiative by the Electric Vehicle Council (EVC)

Welcome to the Charge@Large initiative! This platform, spearheaded by the Electric Vehicle Council (EVC), invites the participation of Charge Point Operators (CPOs) across Australia to enhance the visibility and reliability of public EV charging infrastructure. This README provides an overview of the platform’s goals, features, data collection, and participation benefits.

## 🎯 Project Purpose

The Charge@Large platform serves two main purposes:
1. **Live Status Visualization**: A portal displaying the real-time availability of public EV charging equipment across Australia.
2. **Uptime and Utilization Reporting**: Provides critical uptime and utilization data to government bodies, beginning with the DCCEEW in New South Wales (NSW).

This initiative aims to bridge the existing gap between the live status provided by CPO networks and the aggregated, static information found on existing platforms like Plugshare. By consolidating live availability data from multiple networks, the platform will provide a seamless experience for EV drivers across Australia. Additionally, the uptime and utilization data will support government programs in promoting reliable public EV charging infrastructure.

## 🌟 Key Features

- **Live Availability**: Displays the real-time status of chargers across participating CPO networks to help EV drivers quickly locate operational charging points.
- **Uptime and Utilization Reporting**: Logs status observations to generate reports at the EVSE connector, EV charger, and site levels for government reporting. This data is intended for government use only.
- **Secure Data Collection**: Data is collected via secure methods, including a RESTful API endpoint, OCPI protocol, or WebSocket as per mutual agreement with CPOs.

## 🚫 Platform Limitations

This platform will **not**:
- Act as a payment service or gateway.
- Collect data from unmanaged or non-software-monitored charging sites.
- Capture data on energy throughput (kWh), momentary power output, or driver-specific information.
- Share collected data with private entities.

## 🌍 Why Participate?

- **Enhanced Visibility for Drivers**: A free, industry-led platform that aggregates live status across networks offers EV drivers a reliable tool to locate public charging stations.
- **Promotes EV Adoption**: Public charging reliability is crucial for EV uptake. By participating, CPOs contribute to a more sustainable and accessible EV charging ecosystem, potentially avoiding the need for stringent regulatory interventions.
- **Access to Government Grants**: Some state government grant programs require CPO participation in this platform to be eligible for financial support.

## 📊 Data Collection Overview

To fulfill uptime and utilization reporting requirements, the platform will collect:
- **EV Charger Site Location Data**: Includes site coordinates and addresses for CPO networks.
- **EVSE Connector Details**: Connector type and power rating.
- **Connector Status Observations**: Type, date, and time of status updates.
  - **Frequency**: Ideally, status updates are collected at a high frequency (once per minute); however, data collection intervals may vary based on CPO agreements.
- **Data Collection Methods**: RESTful API endpoint, OCPI protocol, or WebSocket, ensuring flexibility and security in data transfer.

## 🔒 Security and Confidentiality

All data collection and handling adhere to strict security protocols to protect confidentiality and data integrity. The EVC is committed to ensuring that only essential data is collected and shared exclusively with relevant government departments.

## 🚀 How to Get Started

To join the Charge@Large initiative and start contributing to this industry-wide effort for better EV infrastructure, please contact the EVC team.
