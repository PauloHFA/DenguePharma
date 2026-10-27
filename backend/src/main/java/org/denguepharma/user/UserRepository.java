package org.denguepharma.user;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface UserRepository extends JpaRepository<AppUser, UUID> {

    @Query("select u from AppUser u where lower(u.email) = lower(?1)")
    Optional<AppUser> findByEmailIgnoreCase(String email);
}

