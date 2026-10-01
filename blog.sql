-- Script de création de la base "blog" à partir du MPD (MySQL)

CREATE DATABASE IF NOT EXISTS blog
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE blog;

-- -----------------------------------------------------
-- Table users
-- -----------------------------------------------------
CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  deleted_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table categories
-- -----------------------------------------------------
CREATE TABLE categories (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_categories_title (title)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table tags
-- -----------------------------------------------------
CREATE TABLE tags (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tags_title (title)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table articles
-- -----------------------------------------------------
CREATE TABLE articles (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(150) NOT NULL,
  content TEXT NOT NULL,
  published_at DATETIME NULL,
  users_id INT NOT NULL,
  categories_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  deleted_at DATETIME NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_articles_users
    FOREIGN KEY (users_id) REFERENCES users (id),
  CONSTRAINT fk_articles_categories
    FOREIGN KEY (categories_id) REFERENCES categories (id)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table comments
-- -----------------------------------------------------
CREATE TABLE comments (
  id INT NOT NULL AUTO_INCREMENT,
  content TEXT NOT NULL,
  users_id INT NOT NULL,
  articles_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  deleted_at DATETIME NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_comments_users
    FOREIGN KEY (users_id) REFERENCES users (id),
  CONSTRAINT fk_comments_articles
    FOREIGN KEY (articles_id) REFERENCES articles (id)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table articles_tags (table de liaison)
-- -----------------------------------------------------
CREATE TABLE articles_tags (
  articles_id INT NOT NULL,
  tags_id INT NOT NULL,
  PRIMARY KEY (articles_id, tags_id),
  CONSTRAINT fk_articles_tags_articles
    FOREIGN KEY (articles_id) REFERENCES articles (id),
  CONSTRAINT fk_articles_tags_tags
    FOREIGN KEY (tags_id) REFERENCES tags (id)
) ENGINE=InnoDB;
