"""Shipping & Logistics Engine — FedEx / UPS integration with rate shopping."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class ShippingProvider:
    def get_rates(self, origin: Dict, destination: Dict, package: Dict) -> List[Dict]:
        raise NotImplementedError

    def create_shipment(self, origin: Dict, destination: Dict, package: Dict, service: str) -> Dict:
        raise NotImplementedError

    def track(self, tracking_number: str) -> Dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# FedEx
# ---------------------------------------------------------------------------
class FedExProvider(ShippingProvider):
    def __init__(self, api_key: str, secret_key: str, account_number: str, meter_number: str, test_mode: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.account_number = account_number
        self.meter_number = meter_number
        self.base = "https://apis-sandbox.fedex.com" if test_mode else "https://apis.fedex.com"
        self._token: Optional[str] = None

    def _auth(self) -> str:
        if self._token:
            return self._token
        r = requests.post(
            f"{self.base}/oauth/token",
            params={"grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key},
            timeout=15,
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json"}

    def get_rates(self, origin: Dict, destination: Dict, package: Dict) -> List[Dict]:
        payload = {
            "accountNumber": {"value": self.account_number},
            "requestedShipment": {
                "shipper": {"address": _addr(origin)},
                "recipient": {"address": _addr(destination)},
                "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                "rateRequestType": ["PREFERRED", "ACCOUNT"],
                "requestedPackageLineItems": [_pkg_item(package)],
            },
        }
        try:
            r = requests.post(f"{self.base}/rate/v1/rates/quotes", json=payload, headers=self._headers(), timeout=20)
            r.raise_for_status()
            rates = []
            for rd in r.json().get("output", {}).get("rateReplyDetails", []):
                charges = rd.get("ratedShipmentDetails", [{}])[0].get("totalNetChargeWithDutiesAndTaxes", rd.get("ratedShipmentDetails", [{}])[0].get("totalNetCharge", 0))
                rates.append({
                    "service_type": rd.get("serviceType"),
                    "service_name": rd.get("serviceName", ""),
                    "total_charge": float(charges) if charges else 0,
                    "currency": "USD",
                    "transit_days": rd.get("commit", {}).get("daysInTransit", 0),
                })
            return rates
        except Exception as exc:
            logger.error("FedEx rates error: %s", exc)
            return []

    def create_shipment(self, origin: Dict, destination: Dict, package: Dict, service: str) -> Dict:
        payload = {
            "accountNumber": {"value": self.account_number},
            "requestedShipment": {
                "shipper": {"address": _addr(origin)},
                "recipient": {"address": _addr(destination)},
                "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                "serviceType": service,
                "requestedPackageLineItems": [_pkg_item(package)],
            },
        }
        try:
            r = requests.post(f"{self.base}/ship/v1/shipments", json=payload, headers=self._headers(), timeout=20)
            r.raise_for_status()
            data = r.json().get("output", {}).get("transactionShipments", [{}])[0]
            return {
                "success": True,
                "tracking_number": data.get("masterTrackingNumber"),
                "label_url": (data.get("pieceResponses", [{}])[0].get("packageDocuments", [{}])[0].get("url")),
                "shipment_id": data.get("shipmentId"),
            }
        except Exception as exc:
            logger.error("FedEx shipment error: %s", exc)
            return {"success": False, "error": str(exc)}

    def track(self, tracking_number: str) -> Dict:
        try:
            r = requests.get(f"{self.base}/track/v1/trackingnumbers/{tracking_number}", headers=self._headers(), timeout=15)
            r.raise_for_status()
            result = r.json().get("output", {}).get("completeTrackResults", [{}])[0].get("trackResults", [{}])[0]
            return {
                "success": True,
                "status": result.get("statusDescription"),
                "estimated_delivery": next((dt.get("date") for dt in result.get("dateAndTimes", []) if dt.get("type") == "ESTIMATED_DELIVERY"), None),
                "last_update": result.get("lastUpdatedDateTime"),
                "events": result.get("scanEvents", []),
            }
        except Exception as exc:
            logger.error("FedEx track error: %s", exc)
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# UPS
# ---------------------------------------------------------------------------
class UPSProvider(ShippingProvider):
    def __init__(self, api_key: str, username: str, password: str, test_mode: bool = True):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.base = "https://wwwcie.ups.com" if test_mode else "https://onlinetools.ups.com"
        self._token: Optional[str] = None

    def _auth(self) -> str:
        if self._token:
            return self._token
        import base64
        cred = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        r = requests.post(
            f"{self.base}/security/v1/oauth/token",
            params={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {cred}", "Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json"}

    def get_rates(self, origin: Dict, destination: Dict, package: Dict) -> List[Dict]:
        payload = {
            "RateRequest": {
                "Request": {"RequestOption": "Rate"},
                "Shipment": {
                    "Shipper": {"Address": {"PostalCode": origin.get("postal_code"), "CountryCode": origin.get("country", "US")}},
                    "ShipTo": {"Address": {"PostalCode": destination.get("postal_code"), "CountryCode": destination.get("country", "US")}},
                    "Package": {
                        "PackagingType": {"Code": "02"},
                        "Dimensions": {"UnitOfMeasurement": {"Code": "IN"}, "Length": str(package.get("length", 10)), "Width": str(package.get("width", 10)), "Height": str(package.get("height", 10))},
                        "PackageWeight": {"UnitOfMeasurement": {"Code": "LBS"}, "Weight": str(package.get("weight", 1))},
                    },
                },
            }
        }
        try:
            r = requests.post(f"{self.base}/api/rating/v1/rate", json=payload, headers=self._headers(), timeout=20)
            r.raise_for_status()
            rates = []
            for rs in r.json().get("RateResponse", {}).get("RatedShipment", []):
                rates.append({
                    "service_type": rs.get("Service", {}).get("Code"),
                    "service_name": rs.get("Service", {}).get("Description"),
                    "total_charge": float(rs.get("TotalCharges", {}).get("MonetaryValue", 0)),
                    "currency": rs.get("TotalCharges", {}).get("CurrencyCode", "USD"),
                })
            return rates
        except Exception as exc:
            logger.error("UPS rates error: %s", exc)
            return []

    def create_shipment(self, origin: Dict, destination: Dict, package: Dict, service: str) -> Dict:
        payload = {
            "ShipmentRequest": {
                "Request": {"RequestOption": "validate"},
                "Shipment": {
                    "Shipper": {"Name": origin.get("name", "Sender"), "Address": {"AddressLine": [origin.get("street")], "City": origin.get("city"), "StateProvinceCode": origin.get("state"), "PostalCode": origin.get("postal_code"), "CountryCode": origin.get("country", "US")}},
                    "ShipTo": {"Name": destination.get("name"), "Address": {"AddressLine": [destination.get("street")], "City": destination.get("city"), "StateProvinceCode": destination.get("state"), "PostalCode": destination.get("postal_code"), "CountryCode": destination.get("country", "US")}},
                    "Service": {"Code": service},
                    "Package": {"PackagingType": {"Code": "02"}, "Dimensions": {"UnitOfMeasurement": {"Code": "IN"}, "Length": str(package.get("length", 10)), "Width": str(package.get("width", 10)), "Height": str(package.get("height", 10))}, "PackageWeight": {"UnitOfMeasurement": {"Code": "LBS"}, "Weight": str(package.get("weight", 1))}},
                },
                "LabelSpecification": {"LabelImageFormat": {"Code": "PDF"}},
            }
        }
        try:
            r = requests.post(f"{self.base}/api/shipment/v1/ship", json=payload, headers=self._headers(), timeout=20)
            r.raise_for_status()
            ship = r.json().get("ShipmentResponse", {}).get("ShipmentResults", {})
            return {
                "success": True,
                "tracking_number": ship.get("ShipmentIdentificationNumber"),
                "label_url": ship.get("PackageResults", {}).get("ShippingLabel", {}).get("GraphicImage"),
                "shipment_id": ship.get("ShipmentIdentificationNumber"),
            }
        except Exception as exc:
            logger.error("UPS shipment error: %s", exc)
            return {"success": False, "error": str(exc)}

    def track(self, tracking_number: str) -> Dict:
        try:
            r = requests.get(f"{self.base}/api/tracking/v1/tracking/{tracking_number}", headers=self._headers(), timeout=15)
            r.raise_for_status()
            ship = r.json().get("TrackResponse", {}).get("Shipment", {})
            activities = ship.get("Activity", [])
            return {
                "success": True,
                "status": ship.get("Status", {}).get("Description"),
                "estimated_delivery": ship.get("ScheduledDeliveryDate"),
                "last_update": activities[-1].get("Date") if activities else None,
                "events": [
                    {"date": a.get("Date"), "time": a.get("Time"), "description": a.get("Status", {}).get("Description"), "location": a.get("Location", {}).get("Address", {})}
                    for a in activities
                ],
            }
        except Exception as exc:
            logger.error("UPS track error: %s", exc)
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class ShippingEngine:
    def __init__(self, config: Dict[str, Any]):
        self.providers: Dict[str, ShippingProvider] = {}
        if config.get("fedex"):
            fc = config["fedex"]
            self.providers["fedex"] = FedExProvider(fc["api_key"], fc["secret_key"], fc["account_number"], fc["meter_number"], fc.get("test_mode", True))
        if config.get("ups"):
            uc = config["ups"]
            self.providers["ups"] = UPSProvider(uc["api_key"], uc["username"], uc["password"], uc.get("test_mode", True))
        self.default = config.get("default_provider", "fedex")

    def get_rates(self, origin: Dict, destination: Dict, package: Dict, provider: str = None) -> List[Dict]:
        p = provider or self.default
        return self.providers[p].get_rates(origin, destination, package) if p in self.providers else []

    def get_best_rate(self, origin: Dict, destination: Dict, package: Dict) -> Optional[Dict]:
        all_rates: List[Dict] = []
        for name, prov in self.providers.items():
            for r in prov.get_rates(origin, destination, package):
                r["provider"] = name
                all_rates.append(r)
        if not all_rates:
            return None
        all_rates.sort(key=lambda r: r.get("total_charge", float("inf")))
        return all_rates[0]

    def create_shipment(self, origin: Dict, destination: Dict, package: Dict, provider: str = None, service: str = None) -> Dict:
        p = provider or self.default
        if p not in self.providers:
            return {"success": False, "error": f"Provider {p} not configured"}
        return self.providers[p].create_shipment(origin, destination, package, service)

    def track(self, tracking_number: str, provider: str = None) -> Dict:
        if not provider:
            provider = self._detect(tracking_number)
        if provider not in self.providers:
            return {"success": False, "error": f"Provider {provider} not configured"}
        return self.providers[provider].track(tracking_number)

    def _detect(self, tn: str) -> str:
        tn = tn.strip().upper()
        if tn.startswith("1Z"):
            return "ups"
        if len(tn) == 12 and tn.isdigit():
            return "fedex"
        if len(tn) in (18, 22) and tn.isdigit():
            return "ups"
        return self.default


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _addr(d: Dict) -> Dict:
    return {
        "postalCode": d.get("postal_code"),
        "countryCode": d.get("country", "US"),
        "stateOrProvinceCode": d.get("state"),
        "city": d.get("city"),
        "streetLines": [d.get("street", "")],
    }


def _pkg_item(p: Dict) -> Dict:
    return {
        "weight": {"units": "LB", "value": p.get("weight", 1)},
        "dimensions": {"length": p.get("length", 10), "width": p.get("width", 10), "height": p.get("height", 10), "units": "IN"},
    }
