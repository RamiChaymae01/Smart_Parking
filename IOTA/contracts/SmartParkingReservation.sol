// =========================
// SmartParkingReservation.sol (identique à ton code)
// =========================
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SmartParkingReservation is ERC721, Ownable {

    enum Status { None, Reserved, Cancelled, Arrived, NoShow }

    struct Reservation {
        address user;   //Conducteur
        bytes32 slotHash; // Place réservé
        uint64 createdAt;
        uint64 deadline; // limite, par exp : 15min 
        uint256 amountWei; // prix payé
        Status status;
    }

    uint256 public basePriceWei;
    uint256 public penaltyBps;              // 2000 = 20%
    uint256 public reserveWindowSec;        // 15 min
    address public treasury;      //portefeuille

    bool public nftEnabled = true;

    uint256 public nextId = 1;

    mapping(uint256 => Reservation) public reservations;
    mapping(bytes32 => uint256) public activeBySlot;
    mapping(address => uint16) public trustScore;
    mapping(address => uint256[]) private userHistory;

    event ReservationCreated(
        uint256 indexed id,
        address indexed user,
        bytes32 indexed slotHash,
        uint256 price,
        uint64 createdAt,
        uint64 deadline,
        uint16 trustScore
    );

    event ReservationCancelled(
        uint256 indexed id,
        address indexed user,
        uint256 refund,
        uint256 penalty,
        bool beforeDeadline,
        uint16 trustScore
    );

    event ArrivedConfirmed(
        uint256 indexed id,
        address indexed user,
        uint256 paid,
        bool arrivedOnTime,
        uint16 trustScore
    );

    event NoShowFinalized(
        uint256 indexed id,
        address indexed user,
        uint256 refund,
        uint256 penalty,
        uint16 trustScore
    );

    constructor(
        address _treasury,
        uint256 _basePriceWei,
        uint256 _penaltyBps,
        uint256 _reserveWindowSec
    )
        ERC721("ParkingReservationPass", "PRP")
        Ownable(msg.sender)
    {
        require(_treasury != address(0), "treasury=0");
        require(_penaltyBps <= 10000, "penalty too high");

        treasury = _treasury;
        basePriceWei = _basePriceWei;
        penaltyBps = _penaltyBps;
        reserveWindowSec = _reserveWindowSec;
    }

    function _effectiveScore(address user) internal view returns (uint16) {
        uint16 s = trustScore[user];
        return s == 0 ? 50 : s;
    }

    function getPrice(address user) public view returns (uint256) {
        uint16 s = _effectiveScore(user);

        if (s < 40) return (basePriceWei * 120) / 100;
        if (s > 80) return (basePriceWei * 80) / 100;

        return basePriceWei;
    }

    function reserve(string calldata slot) external payable returns (uint256 id) {
        bytes32 h = keccak256(bytes(slot));
        require(activeBySlot[h] == 0, "slot reserved");

        uint256 price = getPrice(msg.sender);
        require(msg.value >= price, "payment too low");

        id = nextId++;

        uint64 nowTs = uint64(block.timestamp);
        uint64 deadline = uint64(block.timestamp + reserveWindowSec);

        reservations[id] = Reservation(
            msg.sender,
            h,
            nowTs,
            deadline,
            price,
            Status.Reserved
        );

        activeBySlot[h] = id;
        userHistory[msg.sender].push(id);

        if (msg.value > price) {
            _transferETH(msg.sender, msg.value - price);
        }

        if (nftEnabled) {
            _safeMint(msg.sender, id);
        }

        emit ReservationCreated(
            id,
            msg.sender,
            h,
            price,
            nowTs,
            deadline,
            _effectiveScore(msg.sender)
        );
    }

    function cancel(uint256 id) external {
        Reservation storage r = reservations[id];
        require(r.status == Status.Reserved, "not reserved");
        require(r.user == msg.sender, "not owner");

        activeBySlot[r.slotHash] = 0;

        bool before = block.timestamp <= r.deadline;
        uint256 penalty = 0;
        uint256 refund = r.amountWei;

        if (before) {
            // stable score
        } else {
            penalty = (r.amountWei * penaltyBps) / 10000;
            refund -= penalty;
            _updateScore(msg.sender, 10, false);
            _transferETH(treasury, penalty);
        }

        r.status = Status.Cancelled;

        if (nftEnabled && _ownerOf(id) != address(0)) {
            _burn(id);
        }

        _transferETH(msg.sender, refund);

        emit ReservationCancelled(
            id,
            msg.sender,
            refund,
            penalty,
            before,
            _effectiveScore(msg.sender)
        );
    }

    function confirmArrival(uint256 id) external onlyOwner {
        Reservation storage r = reservations[id];
        require(r.status == Status.Reserved, "not reserved");

        activeBySlot[r.slotHash] = 0;

        bool onTime = block.timestamp <= r.deadline;

        r.status = Status.Arrived;

        if (nftEnabled && _ownerOf(id) != address(0)) {
            _burn(id);
        }

        _transferETH(treasury, r.amountWei);

        if (onTime) {
            _updateScore(r.user, 10, true);
        }

        emit ArrivedConfirmed(
            id,
            r.user,
            r.amountWei,
            onTime,
            _effectiveScore(r.user)
        );
    }

    function finalizeNoShow(uint256 id) external {
        Reservation storage r = reservations[id];
        require(r.status == Status.Reserved, "not reserved");
        require(block.timestamp > r.deadline, "too early");

        activeBySlot[r.slotHash] = 0;

        uint256 penalty = (r.amountWei * penaltyBps) / 10000;
        uint256 refund = r.amountWei - penalty;

        r.status = Status.NoShow;

        if (nftEnabled && _ownerOf(id) != address(0)) {
            _burn(id);
        }

        _transferETH(treasury, penalty);
        _transferETH(r.user, refund);

        _updateScore(r.user, 20, false);

        emit NoShowFinalized(
            id,
            r.user,
            refund,
            penalty,
            _effectiveScore(r.user)
        );
    }

    function _updateScore(address user, uint16 amount, bool inc) internal {
        uint16 s = _effectiveScore(user);

        if (inc) {
            s += amount;
            if (s > 100) s = 100;
        } else {
            s = s > amount ? s - amount : 0;
        }

        trustScore[user] = s;
    }

    function getUserReservations(address user) external view returns (uint256[] memory) {
        return userHistory[user];
    }

    function _transferETH(address to, uint256 amount) internal {
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "transfer failed");
    }

    receive() external payable {}
}
