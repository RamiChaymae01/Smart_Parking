const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("Deployer:", deployer.address);
  console.log("Balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  // treasury = wallet parking (tu peux remplacer par une adresse fixe)
  const treasury = deployer.address;

  // base price = 0.1 token (comme ton code python)
  const basePriceWei = hre.ethers.parseEther("0.1");

  // penalty = 20% 
  const penaltyBps = 2000;

  // 15 minutes
  const reserveWindowSec = 0.05 * 60;

  const Contract = await hre.ethers.getContractFactory("SmartParkingReservation");
  const c = await Contract.deploy(treasury, basePriceWei, penaltyBps, reserveWindowSec);
  await c.waitForDeployment();

  console.log("SmartParkingReservation deployed to:", await c.getAddress());
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
