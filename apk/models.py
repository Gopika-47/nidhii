from django.db import models

class branch(models.Model):
    B_id  = models.CharField(max_length=100,primary_key=True)  
    Branch_code = models.CharField(max_length=100)  
    Branch_name = models.CharField(max_length=150, null=True, default=None)
    active = models.CharField(max_length=4)

    def __str__(self):
        return self.Branch_name


class registration(models.Model):
    Username = models.CharField(max_length=150)
    Password = models.CharField(max_length=150, null=True, default=None, blank=True)
    Company = models.CharField(max_length=150, blank=True)
    B_id = models.ForeignKey(branch, on_delete=models.CASCADE, to_field='B_id', null=True, default=None)  
    User_level = models.CharField(max_length=50)
    Status = models.CharField(max_length=50)

    def __str__(self):
        return self.Username

class acdet(models.Model):
    Pkac_code = models.CharField(max_length=11500)  
    Ac_name = models.CharField(max_length=150, null=True, default=None)
    Ac_type = models.CharField(max_length=50, null=True, default=None)
    Ac_nature = models.CharField(max_length=50, null=True, default=None)
    Sh_code = models.CharField(max_length=150, null=True, default=None)
    Sh_name = models.CharField(max_length=150, null=True, default=None)
    Company = models.CharField(max_length=150)
    Branch = models.CharField(max_length=150, blank=True, default="All")
    Sub_l = models.CharField(max_length=150)
    HOBR = models.CharField(max_length=150, null=True, default=None)
    Sys_date_time = models.DateTimeField(blank=True)
    Sub_code = models.CharField(max_length=150, blank=True, default="0000")
    Sub_name = models.CharField(max_length=150, blank=True, default="Nil")


class temp_daybook(models.Model):
    Fk_accode = models.CharField(max_length=150)
    Sub_code = models.CharField(max_length=150)
    Branch_code = models.CharField(max_length=150, null=True, default=None)
    User_id = models.IntegerField()
    Trans_id = models.IntegerField()
    Ac_date = models.DateField(null=True, default=None)
    Mode = models.CharField(max_length=150, null=True, default=None)
    Trans_amount = models.FloatField(null=True, default=None)
    crcode = models.CharField(max_length=100,blank=True)
    Narration = models.TextField(null=True, default=None)
    Remark = models.CharField(max_length=150, blank=True)
    Type = models.CharField(max_length=150)
    Bank = models.CharField(max_length=100, blank=True)
    # Post = models.CharField(max_length=5, null=True, default=None)
    # Cr_code = models.CharField(max_length=10)
    # Del_code = models.IntegerField(null=True, default=None)
    # Enter_By = models.IntegerField()
    # Cheque_no = models.CharField(max_length=15, blank=True)

    @property
    def get_account_name(self):
        acc = acdet.objects.filter(Pkac_code=self.Fk_accode).first()
        return acc.Ac_name if acc else ''

    @property
    def get_sub_name(self):
        acc = acdet.objects.filter(Pkac_code=self.Fk_accode, Sub_code=self.Sub_code).first()
        return acc.Sub_name if acc else ''


class Staff(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    MARITAL_STATUS = [('Single', 'Single'), ('Married', 'Married')]

    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    dob = models.DateField()
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS)

    relation = models.CharField(max_length=100)
    relation_name = models.CharField(max_length=100)

    photo = models.FileField(upload_to='staff_photos/', blank=True, null=True)
    signature = models.FileField(upload_to='staff_signatures/', blank=True, null=True)

    house_name = models.CharField(max_length=100)
    house_no = models.CharField(max_length=20)
    place = models.CharField(max_length=100)
    post_office = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    mobile1 = models.CharField(max_length=15)
    mobile2 = models.CharField(max_length=15, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    Branch_code = models.CharField(max_length=30, null=True, default=None)

    def __str__(self):
        return self.name
