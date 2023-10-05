import aiohttp
import datetime
import asyncio
from .credentials import StreamElements
from .database import Donation


class DonationHandler:
    def __init__(self, jwt_token, channel_id):
        self.jwt = jwt_token
        self.cID = channel_id

        self.completeDonations = []

    async def getUnityTips(self):
        donations = await self.get_tips()
        validDonations = ""

        for donation in donations:
            
            
            currentTime = datetime.datetime.now().astimezone()

            difference = (currentTime - donation.date).total_seconds()


            if (difference < 1801):
                validDonations = f"{validDonations}uibImKsUsR{donation.username}"

        return validDonations

    async def get_tips(self) -> list[Donation]:
        try:
            async with aiohttp.ClientSession() as session:

                headers = {
                    "Authorization": self.jwt,
                    "Accept": "application/json; charset=utf-8"
                }

                async with session.get(f"https://api.streamelements.com/kappa/v2/tips/{self.cID}", headers=headers) as data:
                    json = await data.json()
                    donations = [donation for donation in json["docs"]]

                    donation_records = []
                    
                    for donation in donations:
                        donation_record = Donation(
                            id = donation["_id"],
                            username = donation["donation"]["user"]["username"],
                            text = donation["donation"]["message"],
                            email = donation["donation"]["user"].get("email"),
                            donation_amount = donation["donation"]["amount"],
                            isodate=donation["createdAt"]
                        )

                        
                        donation_records.append(donation_record)
                    
                
                    
                    return donation_records
        except Exception as err:
            print(err)
            return await self.get_tips()
                    
    async def fakeTip(self, username, amount, message):
        async with aiohttp.ClientSession() as session:

            headers = {
                "Authorization": self.jwt,
                "Accept": "application/json; charset=utf-8"
            }

            data = {
                "user": {
                    "userID": "",
                    "username": username,
                    "email": "email@gmail.com"
                },
                "message": message,
                "amount": amount,
                "currency": "GBP",
                "imported": True
            }
            
            async with session.post(f"https://api.streamelements.com/kappa/v2/tips/{self.cID}", headers=headers, json=data) as res:
                print(res)
