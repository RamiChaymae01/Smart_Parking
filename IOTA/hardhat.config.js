require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.24",
  networks: {
    iota_testnet: {
      url: process.env.IOTA_EVM_TESTNET_URL,
      accounts: [process.env.PRIVATE_KEY],
    },
  },
};
