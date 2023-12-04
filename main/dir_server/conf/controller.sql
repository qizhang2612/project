/*
 Navicat Premium Data Transfer

 Source Server         : real_controller
 Source Server Type    : MySQL
 Source Server Version : 80031
 Source Host           : 127.0.0.1:3306
 Source Schema         : pub_sub

 Target Server Type    : MySQL
 Target Server Version : 80031
 File Encoding         : 65001

 Date: 08/12/2022 08:50:27
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for address
-- ----------------------------
DROP TABLE IF EXISTS `address`;
CREATE TABLE `address` (
  `op` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `topic_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`topic_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for dn
-- ----------------------------
DROP TABLE IF EXISTS `dn`;
CREATE TABLE `dn` (
  `topicXsubscriber` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `path` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `delay` int NOT NULL,
  `bandwidth` int NOT NULL,
  `priority` int NOT NULL,
  PRIMARY KEY (`topicXsubscriber`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for host
-- ----------------------------
DROP TABLE IF EXISTS `host`;
CREATE TABLE `host` (
  `host_name` varchar(255) NOT NULL,
  `type` varchar(255) NOT NULL,
  `location` varchar(255) NOT NULL,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `ip` varchar(255) NOT NULL,
  PRIMARY KEY (`host_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for pub
-- ----------------------------
DROP TABLE IF EXISTS `pub`;
CREATE TABLE `pub` (
  `topic_name` varchar(255) NOT NULL,
  `type` varchar(255) CHARACTER SET utf16 COLLATE utf16_general_ci NOT NULL,
  `location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `ip` varchar(255) NOT NULL,
  `group_addr` varchar(255) NOT NULL,
  PRIMARY KEY (`topic_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for sub
-- ----------------------------
DROP TABLE IF EXISTS `sub`;
CREATE TABLE `sub` (
  `topic_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `subscriber` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`subscriber`,`topic_name`),
  KEY `pub-sub` (`topic_name`),
  CONSTRAINT `pub-sub` FOREIGN KEY (`topic_name`) REFERENCES `pub` (`topic_name`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for topoedges
-- ----------------------------
DROP TABLE IF EXISTS `topoedges`;
CREATE TABLE `topoedges` (
  `srcXdst` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `src_port` int NOT NULL,
  `dst_port` int NOT NULL,
  `bandwidth` float(10,3) NOT NULL,
  `delay` float(10,3) NOT NULL,
  PRIMARY KEY (`srcXdst`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for toponodes
-- ----------------------------
DROP TABLE IF EXISTS `toponodes`;
CREATE TABLE `toponodes` (
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
