#  Hardhat Project

This repository contains the smart contract and scripts used to :
    - NFT-based reservation
    - Escrow mechanism
    - Arrival confirmation
    - No-show enforcement
    - Trust score updates

---

## 1. Install Dependencies

After cloning the repository, run:

```bash
npm install
```
This command installs all required packages and recreates the `node_modules` folder.

---

## 2. Compile the Smart Contract

To compile the Solidity contracts, execute:
```bash
npx hardhat compile
```

This command generates the necessary artifacts and cache files.

---

## 3. Deploy on IOTA Testnet

To deploy the contract on the IOTA EVM test network, run:
```bash
npx hardhat run scripts/deploy.js --network iota_testnet
```
The deployed contract address will be displayed in the terminal.

---

## 4. Contract Address After Deployment

After executing the deployment command, the terminal will display a message similar to: *SmartParkingReservation deployed to: 0x*

⚠ This address is very important.  
It represents the deployed smart contract on IOTA EVM and will be required for:

- interacting with the contract from scripts  
- executing evaluation scenarios  
- verifying transactions on the network  

Make sure to copy and save this address for later use.

---

## Notes

- Create a local `.env` ( PRIVATE_KEY, IOTA_EVM_TESTNET_URL ) file with your own credentials before deployment.  
- Never share real private keys.  
- Use testnet accounts only.

